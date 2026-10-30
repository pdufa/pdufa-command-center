"""Read-only census for a Render-internal PDUFA PostgreSQL connection.

Requires DATABASE_URL supplied securely in the Render job environment.
Prints aggregate counts only; never exports identifiers or credentials.
"""
import json
import os
import re
from collections import Counter

from sqlalchemy import create_engine, text

PATTERN = re.compile(r"^NCT[0-9]{8}$")


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("AUDIT_BLOCKED: DATABASE_URL is missing; no database access attempted")
    if url.startswith("postgresql+psycopg://"):
        url = "postgresql+psycopg2://" + url.split("://", 1)[1]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url.split("://", 1)[1]
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(text("SELECT current_database(), current_user, current_schema()")).one()
                tables = connection.execute(text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') AND table_type = 'BASE TABLE' ORDER BY table_schema, table_name LIMIT 100")).all()
                print(json.dumps({"audit": "database_inventory", "database": identity[0], "user": identity[1], "schema": identity[2], "visible_tables": [{"schema": schema, "table": name} for schema, name in tables], "scientific_analysis_complete": False, "trade_authorized": False}, sort_keys=True))
                table = connection.execute(text("SELECT to_regclass('full_trial_records')")).scalar_one()
                if table is None:
                    tables = connection.execute(text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema') AND table_type = 'BASE TABLE' ORDER BY table_schema, table_name LIMIT 100")).all()
                    print(json.dumps({"audit": "master_trial_identity", "status": "MASTER_TABLE_NOT_FOUND", "visible_tables": [{"schema": schema, "table": name} for schema, name in tables], "scientific_analysis_complete": False, "trade_authorized": False}, sort_keys=True))
                    return
                rows = connection.execute(text("SELECT nct_id FROM full_trial_records"))
                counts = Counter()
                seen = set()
                for (raw_id,) in rows:
                    counts["rows"] += 1
                    identifier = str(raw_id or "").strip()
                    if not identifier:
                        counts["missing_nct"] += 1
                    elif not PATTERN.fullmatch(identifier):
                        counts["invalid_nct"] += 1
                    elif identifier in seen:
                        counts["duplicate_nct"] += 1
                    else:
                        seen.add(identifier)
                        counts["unique_valid_nct"] += 1
                result = {key: counts[key] for key in ("rows", "missing_nct", "invalid_nct", "duplicate_nct", "unique_valid_nct")}
                download_table = connection.execute(text("SELECT to_regclass('full_trial_download')")).scalar_one()
                if download_table is not None:
                    result["download_statuses"] = [dict(row._mapping) for row in connection.execute(text("SELECT status, COUNT(*) AS entries FROM full_trial_download GROUP BY status ORDER BY status"))]
                print(json.dumps({"audit": "master_trial_identity", "database": identity[0], "counts": result, "scientific_analysis_complete": False, "trade_authorized": False}, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
