"""Real PostgreSQL 16 isolated vault acceptance, never connected to Neon/Render.

Only runs with a strictly local, disposable GitHub Actions postgres service:
host 127.0.0.1, database pdufa_vault_ephemeral, user pdufa_vault_test and an
explicit opt-in. All evidence and encryption/recovery keys are synthetic.
"""
from __future__ import annotations
import hashlib
import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
import pytest

from app import medical_original_evidence_vault as vault
from app import medical_original_evidence_key_recovery as recovery

RAW = b"%PDF-1.7\n" + b"Synthetic public original evidence for PostgreSQL vault integration. " * 8
REQUEST = "LOCKED_PRIMARY_SAP"


def _disposable_url():
    if os.getenv("PDUFA_VAULT_EPHEMERAL_POSTGRES_TEST") != "1":
        pytest.skip("Never connect to any external database during normal tests")
    raw = os.getenv("PDUFA_VAULT_TEST_DSN", "")
    try:
        url = make_url(raw)
    except Exception:
        pytest.fail("Disposable Postgres DSN missing or invalid; never use an outside service")
    if (url.drivername != "postgresql+psycopg"
        or url.host not in ("127.0.0.1", "localhost")
        or url.port != 5432
        or url.database != "pdufa_vault_ephemeral"
        or url.username != "pdufa_vault_test"
    ):
        pytest.fail("Refusing anything other than the fixed local disposable Postgres service")
    return raw


def metadata(raw: bytes, version: str) -> dict:
    return {
        "nct":vault.EXACT_NCT,"requestId":REQUEST,
        "documentType":"STATISTICAL_ANALYSIS_PLAN",
        "documentTitle":"Synthetic original evidence never sourced from a patient",
        "documentVersion":version,"documentDate":"2026-11-08",
        "sourceUrl":"https://clinicaltrials.gov/study/NCT06081894",
        "claimedSha256":hashlib.sha256(raw).hexdigest(),
        "contentType":"application/pdf",
    }


def test_real_postgres_16_encrypted_storage_receipts_triggers_and_offline_recovery():
    dburl = _disposable_url()
    # Only a throwaway CI PostgreSQL service is accepted, never Neon or Render.
    engine = create_engine(dburl, pool_pre_ping=True)
    try:
        with engine.connect() as c:
            server_version = int(c.execute(text("SHOW server_version_num")).scalar())
            database_name = c.execute(text("SELECT current_database()")).scalar()
            owner = c.execute(text("SELECT current_user")).scalar()
        assert server_version >= 160000
        assert database_name == "pdufa_vault_ephemeral"
        assert owner == "pdufa_vault_test"

        vault.initialize(engine)  # Real PostgreSQL, no test-only bypass.
        vault.initialize(engine)  # Additive/idempotent DDL.
        assert "medical_original_evidence_vault" in inspect(engine).get_table_names()
        with engine.connect() as c:
            trigger_count = c.execute(text("""SELECT COUNT(*) FROM pg_trigger
                WHERE tgrelid='medical_original_evidence_vault'::regclass
                AND tgname='medical_original_evidence_vault_immutable'""")).scalar()
            assert trigger_count == 1
            encrypted_col = c.execute(text("""SELECT data_type FROM information_schema.columns
                WHERE table_name='medical_original_evidence_vault'
                AND column_name='encrypted_data'""")).scalar()
            assert encrypted_col == "bytea"

        key = os.urandom(32)
        recovery_key = os.urandom(32)
        offline = recovery.wrap_key_for_offline_backup(
            key,recovery_key,key_label="ACACIA_EPHEMERAL_CI_ONLY_V1")
        restored = recovery.restore_key_from_offline_backup(
            offline,recovery_key,expected_label="ACACIA_EPHEMERAL_CI_ONLY_V1")
        assert restored == key
        assert "sourceEncryptionKey" not in offline

        a = vault.deposit(engine,metadata=metadata(RAW,"v1"),
                          original_bytes=RAW,uploaded_by="ephemeral.ci",
                          encryption_key=key)
        version2 = RAW+b"\nSynthetic approved source version two"
        b = vault.deposit(engine,metadata=metadata(version2,"v2"),
                          original_bytes=version2,uploaded_by="ephemeral.ci",
                          encryption_key=key)
        assert b["previousReceiptSha256"] == a["receiptSha256"]
        audit=vault.audit_version_chain(engine,request_id=REQUEST)
        assert audit["receiptChainVerified"] is True
        assert audit["immutableReceiptCount"] == 2
        assert audit["lastReceiptSha256"] == b["receiptSha256"]
        assert audit["clinicalGradesWritten"] == 0
        for record in (a,b):
            checked=vault.verify_at_rest(engine,receipt_id=record["receiptId"],
                                        encryption_key=restored)
            assert checked["sha256Verified"] is True
            assert checked["aesGcmAuthenticationVerified"] is True
            assert checked["medicalGradesWritten"] == 0
            with pytest.raises(vault.VaultError,match="authentication failed"):
                vault.verify_at_rest(engine,receipt_id=record["receiptId"],
                                    encryption_key=os.urandom(32))

        with engine.connect() as c:
            payloads = c.execute(text(
                "SELECT encrypted_data,nonce,receipt_sha256 FROM medical_original_evidence_vault"
            )).mappings().all()
        assert len(payloads) == 2
        assert all(RAW not in bytes(x["encrypted_data"]) for x in payloads)
        assert all(len(bytes(x["nonce"])) == 12 for x in payloads)
        assert all(isinstance(x["receipt_sha256"],str) for x in payloads)

        # Actual PostgreSQL immutability trigger, including TRUNCATE.
        for statement in (
          "UPDATE medical_original_evidence_vault SET uploaded_by='attacker'",
          "DELETE FROM medical_original_evidence_vault",
          "TRUNCATE medical_original_evidence_vault",
        ):
            with pytest.raises(DBAPIError,match="append-only"):
                with engine.begin() as c:
                    c.execute(text(statement))

        # Distinct version/duplicate source unique constraints survive rollback.
        for raw,version in ((RAW,"v3"),(version2+b"changed","v2")):
            with pytest.raises(vault.VaultError,match="source hash or declared document version"):
                vault.deposit(engine,metadata=metadata(raw,version),
                    original_bytes=raw,uploaded_by="ephemeral.ci",encryption_key=key)
        assert vault.audit_version_chain(engine,request_id=REQUEST)["immutableReceiptCount"] == 2

        # Closing and recreating an actual PostgreSQL connection preserves ciphertext.
        engine.dispose()
        reopened=create_engine(dburl,pool_pre_ping=True)
        try:
            assert vault.audit_version_chain(reopened,request_id=REQUEST)["receiptChainVerified"]
            assert vault.verify_at_rest(reopened,receipt_id=a["receiptId"],
                                        encryption_key=restored)["sha256Verified"]
            assert len(vault.list_receipts(reopened,nct=vault.EXACT_NCT)) == 2
            assert all(x["medicalGrade"] is None
                       for x in vault.list_receipts(reopened,nct=vault.EXACT_NCT))
        finally:
            reopened.dispose()
        print("EPHEMERAL_POSTGRES_VAULT_PASS: PostgreSQL 16+, AES-256-GCM, offline synthetic key restore, append-only update/delete/truncate, 2 versions, 0 clinical grades")
    finally:
        engine.dispose()
