"""MAIN original-evidence PostgreSQL role boundary.

Migration: a separate administrator installs the additive schema and grants
the already provisioned pdufa_vault_runtime only SELECT and INSERT.

Runtime: a dedicated connection (never the shared service DATABASE_URL)
must be logged in as that exact low-privilege account. Every request verifies
permissions and table-owner separation. No runtime DDL, schema initialization,
role creation, secret provisioning, Neon/Render mutation, or clinical grades.
"""
from __future__ import annotations

import os
from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from . import medical_original_evidence_vault as vault

RUNTIME_ROLE = "pdufa_vault_runtime"
TABLE = "public.medical_original_evidence_vault"
TRIGGER = "medical_original_evidence_vault_immutable"
REQUIRED_READ = "SELECT"
REQUIRED_WRITE = "INSERT"
DENIED = ("UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


class PrivilegeBoundaryError(ValueError):
    """Never put connection URLs, usernames or key material in errors."""


def _only_postgres(engine) -> None:
    if engine.dialect.name != "postgresql":
        raise PrivilegeBoundaryError("Real isolated PostgreSQL is required")


def migrate_by_administrator(admin_engine) -> dict:
    """Explicit, separately invoked migration path; never call from HTTP.

    Provision a distinct LOGIN role and its password through an approved
    infrastructure/secret manager first. This function neither makes roles
    nor uses production database URLs. The caller must be an administrator.
    """
    _only_postgres(admin_engine)
    with admin_engine.connect() as c:
        role=c.execute(text("""SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,
            rolreplication,rolbypassrls FROM pg_roles WHERE rolname=:name"""),
            {"name":RUNTIME_ROLE}).mappings().first()
        actor=c.execute(text("SELECT current_user,session_user")).one()
        dbowner=c.execute(text("""SELECT pg_get_userbyid(datdba) FROM pg_database
            WHERE datname=current_database()""")).scalar()
    if not role or not role["rolcanlogin"] or any(role[k] for k in (
        "rolsuper","rolcreatedb","rolcreaterole","rolreplication","rolbypassrls"
    )):
        raise PrivilegeBoundaryError("Dedicated limited LOGIN role must be separately provisioned")
    if actor[0]==RUNTIME_ROLE or actor[1]==RUNTIME_ROLE:
        raise PrivilegeBoundaryError("Runtime account cannot perform schema migration")
    # On a blank isolated database the admin creates only the dedicated vault
    # structures; existing unrelated application tables are never altered.
    vault.initialize(admin_engine)
    with admin_engine.begin() as c:
        owner=c.execute(text("""SELECT pg_get_userbyid(c.relowner)
            FROM pg_class c WHERE c.oid=to_regclass(:name)"""),{"name":TABLE}).scalar()
        if owner != actor[0] or owner==RUNTIME_ROLE:
            raise PrivilegeBoundaryError("Vault migration must run under its separate table owner")
        # Does not revoke on unrelated objects or change schema-wide grants.
        c.execute(text("REVOKE ALL ON TABLE public.medical_original_evidence_vault FROM PUBLIC"))
        c.execute(text("REVOKE ALL ON TABLE public.medical_original_evidence_vault FROM pdufa_vault_runtime"))
        c.execute(text("GRANT SELECT, INSERT ON TABLE public.medical_original_evidence_vault TO pdufa_vault_runtime"))
        c.execute(text("GRANT USAGE ON SCHEMA public TO pdufa_vault_runtime"))
        c.execute(text("REVOKE EXECUTE ON FUNCTION public.medical_evidence_vault_reject_change() FROM PUBLIC"))
    return {"role":RUNTIME_ROLE,"schemaOwnedByRuntime":False,
            "requiredGrants":[REQUIRED_READ,REQUIRED_WRITE],
            "forbiddenGrants":list(DENIED),
            "migrationApplied":True,"clinicalGradesWritten":0}


def verify_runtime(engine) -> dict:
    """Fail closed unless the *session* is the actual unprivileged LOGIN role.

    Checking session_user prevents a privileged owner using SET ROLE to mimic
    a limited current_user. Check every invocation; role privileges can change.
    """
    _only_postgres(engine)
    with engine.connect() as c:
        actor=c.execute(text("SELECT current_user,session_user")).one()
        if actor[0]!=RUNTIME_ROLE or actor[1]!=RUNTIME_ROLE:
            raise PrivilegeBoundaryError("Vault runtime must use dedicated non-owner login")
        state=c.execute(text("""SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,
            rolreplication,rolbypassrls FROM pg_roles WHERE rolname=current_user""")
            ).mappings().first()
        owner=c.execute(text("""SELECT pg_get_userbyid(c.relowner)
            FROM pg_class c WHERE c.oid=to_regclass(:name)"""),{"name":TABLE}).scalar()
        db_owner=c.execute(text("""SELECT pg_get_userbyid(datdba)
            FROM pg_database WHERE datname=current_database()""")).scalar()
        flags=c.execute(text("""SELECT
            has_table_privilege(current_user,:table,'SELECT') AS can_select,
            has_table_privilege(current_user,:table,'INSERT') AS can_insert,
            has_table_privilege(current_user,:table,'UPDATE') AS can_update,
            has_table_privilege(current_user,:table,'DELETE') AS can_delete,
            has_table_privilege(current_user,:table,'TRUNCATE') AS can_truncate,
            has_table_privilege(current_user,:table,'REFERENCES') AS can_reference,
            has_table_privilege(current_user,:table,'TRIGGER') AS can_trigger,
            has_schema_privilege(current_user,'public','CREATE') AS can_create,
            has_database_privilege(current_user,current_database(),'CREATE') AS can_create_db
        """),{"table":TABLE}).mappings().one()
        owner_membership=c.execute(text("SELECT pg_has_role(current_user,:owner,'MEMBER')"),
            {"owner":owner}).scalar() if owner else True
        enabled=c.execute(text("""SELECT t.tgenabled, t.tgtype,
                   pg_get_userbyid(p.proowner) AS function_owner,
                   p.proname AS function_name
            FROM pg_trigger t
            JOIN pg_class cl ON cl.oid=t.tgrelid
            JOIN pg_proc p ON p.oid=t.tgfoid
            WHERE cl.oid=to_regclass(:table)
              AND t.tgname=:name AND NOT t.tgisinternal"""),
            {"table":TABLE,"name":TRIGGER}).mappings().all()
    if not state or not state["rolcanlogin"] or any(state[k] for k in (
        "rolsuper","rolcreatedb","rolcreaterole","rolreplication","rolbypassrls"
    )) or owner is None or owner==RUNTIME_ROLE:
        raise PrivilegeBoundaryError("Vault database role is not least privileged")
    if owner_membership or db_owner==RUNTIME_ROLE or flags["can_create"] or flags["can_create_db"]:
        raise PrivilegeBoundaryError("Vault runtime has schema or database creation permission")
    if not flags["can_select"] or not flags["can_insert"] or any(flags[k] for k in (
        "can_update","can_delete","can_truncate","can_reference","can_trigger"
    )):
        raise PrivilegeBoundaryError("Vault runtime table grants are not SELECT plus INSERT only")
    if (len(enabled)!=1 or enabled[0]["tgenabled"]!="O"
            or enabled[0]["tgtype"]!=58
            or enabled[0]["function_name"]!="medical_evidence_vault_reject_change"
            or enabled[0]["function_owner"]==RUNTIME_ROLE):
        raise PrivilegeBoundaryError("Vault immutability trigger is absent or untrusted")
    return {"runtimeRole":RUNTIME_ROLE,"tableOwnerIsSeparate":True,
            "schemaCreateDenied":True,"databaseCreateDenied":True,
            "selectInsertOnly":True,"appendOnlyTriggerPresent":True,
            "clinicalGradesWritten":0,"fdaPrediction":"ABSTAIN"}


def validate_runtime_database_url(url: str) -> str:
    """Dedicated DSN, never the main service DATABASE_URL."""
    try:
        parsed=make_url(url)
    except Exception:
        raise PrivilegeBoundaryError("Dedicated vault PostgreSQL connection not configured") from None
    if parsed.drivername!="postgresql+psycopg" or parsed.username!=RUNTIME_ROLE:
        raise PrivilegeBoundaryError("Vault DSN must use the exact separate PostgreSQL LOGIN role")
    if not parsed.host or not parsed.database or parsed.port not in (None,5432):
        raise PrivilegeBoundaryError("Vault database host, name or port invalid")
    # Local CI has a tightly named disposable database and test flag; all
    # external database connections require TLS. No remote connection is
    # attempted by this parser.
    local=(parsed.host in ("127.0.0.1","localhost")
           and parsed.database=="pdufa_vault_ephemeral"
           and os.getenv("PDUFA_VAULT_EPHEMERAL_POSTGRES_TEST")=="1")
    if not local and parsed.query.get("sslmode") not in ("verify-full",):
        raise PrivilegeBoundaryError("External vault PostgreSQL requires verify-full TLS")
    if url==os.getenv("DATABASE_URL","__NO_SHARED_DB_CONFIGURED__"):
        raise PrivilegeBoundaryError("Evidence vault may not reuse main service database credentials")
    return url


@lru_cache(maxsize=1)
def get_runtime_engine():
    dsn=validate_runtime_database_url(
        os.getenv("PDUFA_EVIDENCE_RUNTIME_DATABASE_URL",""))
    return create_engine(dsn,pool_pre_ping=True,pool_size=2,max_overflow=0,
                         connect_args={"connect_timeout":5})
