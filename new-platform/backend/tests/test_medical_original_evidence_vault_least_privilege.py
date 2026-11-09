"""Real disposable Postgres tests for MAIN evidence migration/runtime separation.

Only connects to the already-provisioned GitHub Actions localhost PostgreSQL.
The role/password are synthetic, used only in this short-lived container.
No production service, Neon, Render, patient data or actual source document.
"""
from __future__ import annotations

import hashlib
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app import medical_original_evidence_vault as vault
from app import medical_original_evidence_permissions as perms
from app import medical_original_evidence_vault_http as http

FIXED_USER="pdufa_vault_runtime"
TEST_PASSWORD="EPHEMERAL_RUNTIME_ONLY_TEST_PASSWORD_2026"
SOURCE=b"%PDF-1.7\n"+b"Independent synthetic role-security PostgreSQL evidence " * 11

def _admin_url():
    if os.getenv("PDUFA_VAULT_EPHEMERAL_POSTGRES_TEST")!="1":
        pytest.skip("Never use actual databases for role acceptance")
    raw=os.getenv("PDUFA_VAULT_TEST_DSN","")
    from sqlalchemy.engine import make_url
    try:
        parsed=make_url(raw)
    except Exception:
        pytest.fail("Disposable local database not configured")
    assert parsed.drivername=="postgresql+psycopg"
    assert parsed.username=="pdufa_vault_test"
    assert parsed.host=="127.0.0.1"
    assert parsed.port==5432
    assert parsed.database=="pdufa_vault_ephemeral"
    return raw

def _runtime_url():
    return URL.create("postgresql+psycopg",username=FIXED_USER,
                      password=TEST_PASSWORD,host="127.0.0.1",port=5432,
                      database="pdufa_vault_ephemeral")

def _setup_role(admin):
    with admin.begin() as c:
        exists=c.execute(text("SELECT 1 FROM pg_roles WHERE rolname=:r"),
                         {"r":FIXED_USER}).scalar()
        if not exists:
            # EXACT fixed synthetic credentials; no SQL input from user.
            c.execute(text("""CREATE ROLE pdufa_vault_runtime LOGIN
              PASSWORD 'EPHEMERAL_RUNTIME_ONLY_TEST_PASSWORD_2026'
              NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"""))

def _doc(version="v1"):
    return {
      "nct":"NCT06081894","requestId":"HF_SAE_EVENT_DEFINITION",
      "documentType":"HF_ADVERSE_EVENT_TABLE",
      "documentTitle":"Synthetic original safety research source and event definitions",
      "documentVersion":version,"documentDate":"2026-11-08",
      "sourceUrl":"https://clinicaltrials.gov/study/NCT06081894",
      "claimedSha256":hashlib.sha256(SOURCE).hexdigest(),
      "contentType":"application/pdf",
    }

@pytest.mark.postgres_privileges
def test_restricted_postgresql_user_owns_no_schema_and_can_only_append_source_receipts(monkeypatch):
    url=_admin_url()
    admin=create_engine(url,pool_pre_ping=True)
    runtime=None
    try:
        _setup_role(admin)
        migration=perms.migrate_by_administrator(admin)
        assert migration["role"]==FIXED_USER
        assert migration["schemaOwnedByRuntime"] is False
        assert migration["requiredGrants"]==["SELECT","INSERT"]
        assert migration["migrationApplied"] is True

        # The admin is not permitted to masquerade as application runtime.
        with pytest.raises(perms.PrivilegeBoundaryError,match="non-owner login"):
            perms.verify_runtime(admin)

        runtime_url=_runtime_url()
        monkeypatch.setenv("PDUFA_VAULT_EPHEMERAL_POSTGRES_TEST","1")
        assert perms.validate_runtime_database_url(str(runtime_url))==str(runtime_url)
        runtime=create_engine(runtime_url,pool_pre_ping=True)

        preflight=perms.verify_runtime(runtime)
        assert preflight["runtimeRole"]==FIXED_USER
        assert preflight["tableOwnerIsSeparate"] is True
        assert preflight["selectInsertOnly"] is True
        assert preflight["schemaCreateDenied"] is True
        assert preflight["databaseCreateDenied"] is True
        assert preflight["appendOnlyTriggerPresent"] is True
        assert preflight["clinicalGradesWritten"]==0

        # No schema migration may be performed through the runtime engine.
        with pytest.raises(perms.PrivilegeBoundaryError,match="Runtime account"):
            perms.migrate_by_administrator(runtime)
        with pytest.raises(DBAPIError):
            vault.initialize(runtime)

        # UPDATE / DELETE / TRUNCATE / ALTER / DROP / CREATE must all fail
        # even if the attacker knows the exact schema and trial.
        table="public.medical_original_evidence_vault"
        forbidden=[
          f"UPDATE {table} SET uploaded_by='attacker'",
          f"DELETE FROM {table}",
          f"TRUNCATE {table}",
          f"ALTER TABLE {table} ADD COLUMN attacker TEXT",
          f"DROP TABLE {table}",
          "CREATE TABLE public.evidence_vault_unauthorized(id INT)",
        ]
        for sql in forbidden:
            with pytest.raises(DBAPIError):
                with runtime.begin() as c:
                    c.execute(text(sql))

        # Cannot disable immutable trigger, escalate via SET ROLE, or grant.
        for sql in (
          f"ALTER TABLE {table} DISABLE TRIGGER medical_original_evidence_vault_immutable",
          "SET ROLE pdufa_vault_test",
          f"GRANT UPDATE ON {table} TO pdufa_vault_runtime",
        ):
            with pytest.raises(DBAPIError):
                with runtime.begin() as c:
                    c.execute(text(sql))

        # Exact public source bytes encrypt and append, despite no owner power.
        key=os.urandom(32)
        receipt=vault.deposit(runtime,metadata=_doc(),original_bytes=SOURCE,
              uploaded_by="ephemeral.runtime",encryption_key=key)
        assert receipt["encrypted"] is True
        assert receipt["medicalGradesWritten"]==0
        assert receipt["issuerAndClinicalContentIndependentlyVerified"] is False
        assert vault.audit_version_chain(runtime,request_id="HF_SAE_EVENT_DEFINITION")["receiptChainVerified"]
        assert vault.verify_at_rest(runtime,receipt_id=receipt["receiptId"],
                                   encryption_key=key)["sha256Verified"]
        assert vault.list_receipts(runtime,nct="NCT06081894")[0]["medicalGrade"] is None or all(
            row["medicalGrade"] is None
            for row in vault.list_receipts(runtime,nct="NCT06081894"))

        # The ordinary runtime cannot grant itself extra permissions.
        with pytest.raises(DBAPIError):
            with runtime.begin() as c:
                c.execute(text("GRANT DELETE ON public.medical_original_evidence_vault TO pdufa_vault_runtime"))
        assert perms.verify_runtime(runtime)["selectInsertOnly"]
        print("VAULT_POSTGRES_SEPARATE_ROLE_PASS: real PostgreSQL role, no owner/DDL/UPDATE/DELETE/TRUNCATE/GRANT, encrypted append, 0 grades")
    finally:
        if runtime is not None: runtime.dispose()
        admin.dispose()


def test_dedicated_runtime_dsn_refuses_shared_owner_url_and_tls_downgrades(monkeypatch):
    _admin_url()  # skips unless in disposable workflow
    monkeypatch.setenv("PDUFA_VAULT_EPHEMERAL_POSTGRES_TEST","1")
    monkeypatch.setenv("DATABASE_URL","postgresql+psycopg://pdufa_vault_test:pw@127.0.0.1:5432/pdufa_vault_ephemeral")
    for candidate in (
      "sqlite:///tmp/test.db",
      "postgresql+psycopg://pdufa_vault_test:pw@127.0.0.1:5432/pdufa_vault_ephemeral",
      "postgresql+psycopg://other_user:pw@127.0.0.1:5432/pdufa_vault_ephemeral",
      "postgresql+psycopg://pdufa_vault_runtime:pw@127.0.0.1:5432/other_database",
      "postgresql+psycopg://pdufa_vault_runtime:pw@database.external.example:5432/vault",
    ):
        with pytest.raises(perms.PrivilegeBoundaryError):
            perms.validate_runtime_database_url(candidate)
    # External connections must have a verified TLS hostname.
    assert perms.validate_runtime_database_url(
        "postgresql+psycopg://pdufa_vault_runtime:pw@database.external.example:5432/vault?sslmode=verify-full"
    ).endswith("sslmode=verify-full")


def test_runtime_http_will_never_run_migration_ddl(monkeypatch):
    # No database service needed: enforce direct code separation with a spy.
    import types
    class Dialect: name="postgresql"
    class Dummy: dialect=Dialect()
    fake=Dummy()
    monkeypatch.setattr(perms,"verify_runtime",lambda engine: {
        "runtimeRole":perms.RUNTIME_ROLE,"selectInsertOnly":True
    })
    monkeypatch.setattr(vault,"initialize",lambda engine: (_ for _ in ()).throw(
        AssertionError("HTTP attempted a schema migration")))
    http._initialize(fake,lambda:None)  # Should only verify privileges.
    monkeypatch.setattr(perms,"verify_runtime",lambda engine: (
       _ for _ in ()).throw(perms.PrivilegeBoundaryError("no grant")))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        http._initialize(fake,lambda:None)
    assert exc.value.status_code==503
