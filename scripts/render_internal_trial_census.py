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
        print(json.dumps({"audit": "master_trial_identity", "counts": dict(counts), "scientific_analysis_complete": False, "trade_authorized": False}, sort_keys=True))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
