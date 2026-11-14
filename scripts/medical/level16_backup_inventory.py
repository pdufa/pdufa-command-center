"""Read-only integrity inventory for authorized isolated restore comparisons.

No DSN lookup, connection creation, migration, export or restore is performed by
this module. It emits hashes/counts, never original bytes, identities or tokens.
"""
import hashlib
import json
from datetime import date,datetime
from uuid import UUID

TABLES=('reviewer_grants','streams','events','identity_accounts','identity_sessions',
        'revoked_tokens','authorization_audit','original_documents','evidence_bundles',
        'evidence_access','current_evidence_versions')


def normalize(value):
    if isinstance(value,(bytes,bytearray,memoryview)):
        return {'byteCount':len(value),'sha256':hashlib.sha256(bytes(value)).hexdigest()}
    if isinstance(value,(datetime,date)):return value.isoformat()
    if isinstance(value,UUID):return str(value)
    if isinstance(value,dict):return {k:normalize(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalize(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(normalize(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def inventory(connection):
    from sqlalchemy import text
    tables={}
    for table in TABLES:
        rows=connection.execute(text('SELECT * FROM level16_review.'+table)).mappings().all()
        tables[table]={'rowCount':len(rows),'rowDigests':sorted(digest(dict(row)) for row in rows)}
    triggers=[dict(r) for r in connection.execute(text('''SELECT c.relname,t.tgname,t.tgenabled,
        pg_get_triggerdef(t.oid) AS definition FROM pg_trigger t
        JOIN pg_class c ON c.oid=t.tgrelid JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='level16_review' AND NOT t.tgisinternal ORDER BY c.relname,t.tgname''')).mappings()]
    policies=[dict(r) for r in connection.execute(text('''SELECT c.relname,c.relrowsecurity,p.polname,
        pg_get_expr(p.polqual,p.polrelid) AS policy_expression FROM pg_class c
        JOIN pg_namespace n ON n.oid=c.relnamespace LEFT JOIN pg_policy p ON p.polrelid=c.oid
        WHERE n.nspname='level16_review' AND c.relkind='r' ORDER BY c.relname,p.polname''')).mappings()]
    return {'tables':tables,'triggerInventoryDigest':digest(triggers),'policyInventoryDigest':digest(policies)}
