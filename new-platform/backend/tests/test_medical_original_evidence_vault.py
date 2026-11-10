"""MAIN isolated encrypted evidence vault: no production writes and no clinical grades."""
from __future__ import annotations
import base64
from datetime import datetime
import hashlib
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError
import pytest

from app import medical_original_evidence_vault as vault

KEY = b"x"*32
RAW = b"%PDF-1.7\n" + b"Original public Phase III source evidence report for NCT06081894. " * 10


def meta(*, request_id="LOCKED_PRIMARY_SAP", raw=RAW, version="Final 1.0"):
    return {
        "nct":"NCT06081894","requestId":request_id,
        "documentType":vault.REQUEST_TYPES[request_id],
        "documentTitle":"Original ACACIA HCM analysis source candidate",
        "documentVersion":version,"documentDate":"2026-11-01",
        "sourceUrl":"https://clinicaltrials.gov/study/NCT06081894",
        "claimedSha256":hashlib.sha256(raw).hexdigest(),
        "contentType":"application/pdf"
    }


@pytest.fixture
def engine():
    e=create_engine("sqlite+pysqlite:///:memory:")
    vault.initialize(e,test_only=True)
    try:
        yield e
    finally:
        e.dispose()


def deposit(e, raw=RAW, **kwargs):
    return vault.deposit(e,metadata=meta(raw=raw,**kwargs),
                         original_bytes=raw,uploaded_by="research.intake",
                         encryption_key=KEY)


def test_explicit_init_rejects_ephemeral_sqlite_outside_test():
    e=create_engine("sqlite+pysqlite:///:memory:")
    with pytest.raises(vault.VaultError,match="Durable PostgreSQL"):
        vault.initialize(e)
    with e.connect() as c:
        assert not c.execute(text("""SELECT name FROM sqlite_master
            WHERE name='medical_original_evidence_vault'""")).scalar()
    e.dispose()


def test_original_bytes_are_hash_checked_and_encrypted_before_persistence(engine):
    receipt=deposit(engine)
    assert receipt["encrypted"] is True
    assert receipt["receivedOriginalBytes"]==len(RAW)
    assert receipt["sourceHashComputedFromOriginalBytes"] is True
    assert receipt["issuerAndClinicalContentIndependentlyVerified"] is False
    assert receipt["sponsorAuthorizationVerified"] is False
    assert receipt["clinicalReviewerSigned"] is False
    assert receipt["medicalGradesWritten"]==0
    assert receipt["fdaPrediction"]=="ABSTAIN"
    rows=vault.list_receipts(engine,nct="NCT06081894")
    assert len(rows)==1
    assert rows[0]["sourceSha256"]==hashlib.sha256(RAW).hexdigest()
    assert rows[0]["medicalGrade"] is None
    assert rows[0]["clinicalReviewerSigned"] is False
    with engine.connect() as c:
        row=c.execute(text("SELECT encrypted_data,nonce,metadata_json,receipt_sha256 FROM medical_original_evidence_vault")).mappings().one()
    assert RAW not in row["encrypted_data"]
    assert b"Original public Phase III" not in row["encrypted_data"]
    assert len(bytes(row["nonce"]))==12
    assert len(bytes(row["encrypted_data"]))==len(RAW)+16
    assert "Original public Phase III" not in row["metadata_json"]
    assert row["receipt_sha256"]==receipt["receiptSha256"]
    audit=vault.verify_at_rest(engine,receipt_id=receipt["receiptId"],encryption_key=KEY)
    assert audit["sha256Verified"] and audit["aesGcmAuthenticationVerified"]
    assert audit["originalBytesVerified"]==len(RAW)
    assert audit["medicalGradesWritten"]==0
    assert "bytes" not in audit
    assert len(str(audit))<320


def test_two_versions_append_chain_without_overwrite(engine):
    a=deposit(engine)
    raw=RAW+b"v2 new verifiable public source revision"
    b=deposit(engine,raw=raw,version="Final 2.0")
    assert a["previousReceiptSha256"] is None
    assert b["previousReceiptSha256"]==a["receiptSha256"]
    assert b["receiptSha256"]!=a["receiptSha256"]
    assert len(vault.list_receipts(engine,nct="NCT06081894"))==2
    assert vault.verify_at_rest(engine,receipt_id=b["receiptId"],encryption_key=KEY)["sha256Verified"]


def test_chain_audit_verifies_distinct_versions_and_no_scientific_grade(engine):
    assert vault.audit_version_chain(engine,request_id="LOCKED_PRIMARY_SAP")["immutableReceiptCount"]==0
    first=deposit(engine)
    second=deposit(engine,raw=RAW+b"\nVersion-2 original public research appendix",version="Final 2.0")
    audit=vault.audit_version_chain(engine,request_id="LOCKED_PRIMARY_SAP")
    assert audit["immutableReceiptCount"]==2
    assert audit["lastReceiptSha256"]==second["receiptSha256"]
    assert audit["receiptChainVerified"] is True
    assert audit["clinicalGradesWritten"]==0
    assert first["previousReceiptSha256"] is None
    assert second["previousReceiptSha256"]==first["receiptSha256"]
    with pytest.raises(vault.VaultError,match="Unknown source"):
        vault.audit_version_chain(engine,request_id="UNKNOWN")


def test_version_identity_cannot_be_reused_for_modified_original_bytes(engine):
    first=deposit(engine)
    changed=RAW+b"\nNew bytes but falsely reused original version identity"
    with pytest.raises(vault.VaultError,match="declared document version"):
        deposit(engine,raw=changed)
    rows=vault.list_receipts(engine,nct="NCT06081894")
    assert len(rows)==1
    assert rows[0]["documentVersion"]=="Final 1.0"
    assert rows[0]["receiptSha256"]==first["receiptSha256"]


def test_duplicates_rejected_without_rewriting_history(engine):
    a=deposit(engine)
    with pytest.raises(vault.VaultError,match="source hash or declared document version"):
        deposit(engine)
    assert len(vault.list_receipts(engine,nct="NCT06081894"))==1
    assert vault.list_receipts(engine,nct="NCT06081894")[0]["receiptSha256"]==a["receiptSha256"]


@pytest.mark.parametrize("sql",[
    "UPDATE medical_original_evidence_vault SET uploaded_by='attacker'",
    "DELETE FROM medical_original_evidence_vault",
])
def test_database_append_only_trigger_denies_mutation(engine,sql):
    deposit(engine)
    with pytest.raises(DatabaseError,match="append-only"):
        with engine.begin() as c:
            c.execute(text(sql))
    assert len(vault.list_receipts(engine,nct="NCT06081894"))==1


@pytest.mark.parametrize("change",[
    lambda m: m.update(nct="NCT11111111"),
    lambda m: m.update(requestId="UNKNOWN"),
    lambda m: m.update(documentType="REGULATORY_SOURCE"),
    lambda m: m.update(documentTitle="<script>not a title</script>"),
    lambda m: m.update(documentTitle="x"),
    lambda m: m.update(documentVersion=""),
    lambda m: m.update(documentDate="2026-02-30"),
    lambda m: m.update(sourceUrl="http://clinicaltrials.gov/study/NCT06081894"),
    lambda m: m.update(sourceUrl="https://127.0.0.1/private"),
    lambda m: m.update(sourceUrl="https://clinicaltrials.gov.evil.example/fake"),
    lambda m: m.update(sourceUrl="https://clinicaltrials.gov/study/NCT06081894?token=secrets"),
    lambda m: m.update(sourceUrl="https://usr:pass@clinicaltrials.gov/study/NCT06081894"),
    lambda m: m.update(sourceUrl="https://clinicaltrials.gov:5432/study/NCT06081894"),
    lambda m: m.update(claimedSha256="0"*64),
    lambda m: m.update(claimedSha256="NOT_HEX"),
    lambda m: m.update(contentType="application/octet-stream"),
    lambda m: m.update(patientName="DO NOT KEEP"),
])
def test_rejects_mismatched_or_unsafe_source_records(engine,change):
    m=meta()
    change(m)
    with pytest.raises(vault.VaultError):
        vault.deposit(engine,metadata=m,original_bytes=RAW,
                      uploaded_by="research.intake",encryption_key=KEY)
    assert not vault.list_receipts(engine,nct="NCT06081894")


def test_named_role_and_key_security(engine):
    with pytest.raises(vault.VaultError,match="Invalid independently provisioned encryption key"):
        vault.deposit(engine,metadata=meta(),original_bytes=RAW,
                      uploaded_by="research.intake",encryption_key=b"y")
    with pytest.raises(vault.VaultError,match="named"):
        vault.deposit(engine,metadata=meta(),original_bytes=RAW,
                      uploaded_by="unknown actor!",encryption_key=KEY)
    with pytest.raises(vault.VaultError,match="encryption key"):
        vault.parse_encryption_key("garbled")
    assert vault.parse_encryption_key(base64.b64encode(KEY).decode())==KEY


def test_decryption_fails_closed_on_wrong_key(engine):
    receipt=deposit(engine)
    with pytest.raises(vault.VaultError,match="authentication failed"):
        vault.verify_at_rest(engine,receipt_id=receipt["receiptId"],encryption_key=b"z"*32)


def test_unreadable_blob_size_and_media_type_rejected(engine):
    short=b"%PDF-1.7\n"
    with pytest.raises(vault.VaultError,match="byte size"):
        deposit(engine,raw=short)
    fake=b"not a pdf even though it may have a hash"+b"x"*100
    with pytest.raises(vault.VaultError,match="signature"):
        deposit(engine,raw=fake)
    with pytest.raises(vault.VaultError,match="size"):
        deposit(engine,raw=b"%PDF-1.7\n"+b"X"*(vault.MAX_DOCUMENT_BYTES+1))
    assert not vault.list_receipts(engine,nct="NCT06081894")


def test_supports_small_utf8_original_documents_but_no_patient_data_policy(engine):
    txt=b"Published public protocol source version and dated research findings: NCT06081894"
    m=meta(raw=txt)
    m["contentType"]="text/plain"
    r=vault.deposit(engine,metadata=m,original_bytes=txt,
                    uploaded_by="research.intake",encryption_key=KEY)
    assert vault.verify_at_rest(engine,receipt_id=r["receiptId"],encryption_key=KEY)["sha256Verified"]
    malformed=b"Invalid binary text \xff\x00"+b"x"*100
    m=meta(raw=malformed);m["contentType"]="text/plain"
    with pytest.raises(vault.VaultError,match="UTF-8"):
        vault.deposit(engine,metadata=m,original_bytes=malformed,
                      uploaded_by="research.intake",encryption_key=KEY)


def test_only_exact_nct_receipts_and_no_plaintext_in_metadata_lists(engine):
    deposit(engine)
    with pytest.raises(vault.VaultError,match="Wrong trial"):
        vault.list_receipts(engine,nct="NCT00000000")
    assert all("encrypted_data" not in x and "nonce" not in x
               for x in vault.list_receipts(engine,nct="NCT06081894"))
