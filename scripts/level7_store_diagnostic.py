"""Read-only local Level 7 store diagnostic. Never creates or mutates a database.

Run inside an authorized service/container with an existing SQLite evidence path:
    python scripts/level7_store_diagnostic.py --db /secure/path/level7-evidence.sqlite3

Only aggregate counts and schema status are printed; no source payloads or secrets.
"""
from __future__ import annotations
import argparse
import json
import sqlite3
from pathlib import Path

def inspect(path: Path) -> dict:
    if not path.is_file():
        return {"status": "DATABASE_NOT_FOUND", "tablePresent": False}
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        present = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='level7_evidence'"
        ).fetchone() is not None
        if not present:
            return {"status": "LEVEL7_TABLE_NOT_FOUND", "tablePresent": False}
        cols = {row[1] for row in db.execute("PRAGMA table_info(level7_evidence)")}
        required = {"trial_id", "source_id", "source_version", "record_json"}
        if not required.issubset(cols):
            return {"status": "LEVEL7_SCHEMA_MISMATCH", "tablePresent": True}
        total, trials, sources = db.execute(
            "SELECT COUNT(*), COUNT(DISTINCT trial_id), COUNT(DISTINCT trial_id || ':' || source_id) FROM level7_evidence"
        ).fetchone()
        return {"status": "LEVEL7_STORE_FOUND", "tablePresent": True,
                "sourceVersions": total, "trialIdentities": trials,
                "trialSourcePairs": sources}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.db), sort_keys=True))

if __name__ == "__main__":
    main()
