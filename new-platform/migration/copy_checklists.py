"""Non-destructive copy/verify of the new PDUFA checklist table to a new Postgres.

Run from a PRIVATE environment with network access to BOTH databases.
This script never deletes, truncates, or updates the source database.
Require a verified write freeze on the Render API before invoking --copy.

Requirements: pip install -r new-platform/backend/requirements.txt
Example (values must be private environment variables, not pasted into code):
  export MIGRATION_SOURCE_DATABASE_URL="..."
  export MIGRATION_TARGET_DATABASE_URL="..."
  python new-platform/migration/copy_checklists.py --check
  export PDUFA_WRITE_FREEZE_CONFIRMED=yes
  python new-platform/migration/copy_checklists.py --copy
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Column, DateTime, Integer, JSON, MetaData, String, Table, create_engine, func, insert, select
from sqlalchemy.engine import make_url

TABLE_NAME = "checklists"


def url_from_env(name: str):
    value = os.environ.get(name, "")
    if value.startswith("postgres://"):
        value = "postgresql+psycopg://" + value[len("postgres://"):]
    elif value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value[len("postgresql://"):]
    if not value.startswith("postgresql+psycopg://"):
        raise ValueError(name + " must contain an unpooled PostgreSQL connection URL")
    return make_url(value)


def is_same_database(source, target):
    return ((source.host or "").lower(), source.port or 5432, source.database) == (
        (target.host or "").lower(), target.port or 5432, target.database
    )


meta = MetaData()
checklists = Table(
    TABLE_NAME, meta,
    Column("ticker", String(15), primary_key=True),
    Column("stage", String(12), primary_key=True),
    Column("selections", JSON, nullable=False),
    Column("notes", String(4000), nullable=False),
    Column("version", Integer, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def _canonical(row):
    record = dict(row)
    updated_at = record.get("updated_at")
    if isinstance(updated_at, datetime):
        if updated_at.tzinfo is not None:
            updated_at = updated_at.astimezone(timezone.utc)
        record["updated_at"] = updated_at.isoformat()
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def snapshot(conn):
    # Full records are read only inside the private migration process, never logged.
    records = [dict(r) for r in conn.execute(
        select(checklists).order_by(checklists.c.ticker, checklists.c.stage)
    ).mappings()]
    checksum = hashlib.sha256()
    for row in records:
        checksum.update(_canonical(row).encode("utf-8"))
        checksum.update(b"\n")
    return records, checksum.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Safely compare or copy new-platform checklists")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Read-only count/checksum comparison")
    mode.add_argument("--copy", action="store_true", help="Copy source rows once; requires a write freeze")
    args = parser.parse_args()

    source = url_from_env("MIGRATION_SOURCE_DATABASE_URL")
    target = url_from_env("MIGRATION_TARGET_DATABASE_URL")
    if is_same_database(source, target):
        raise ValueError("Source and destination identify the same PostgreSQL database")
    if args.copy and os.environ.get("PDUFA_WRITE_FREEZE_CONFIRMED") != "yes":
        raise ValueError("Refusing to copy without PDUFA_WRITE_FREEZE_CONFIRMED=yes")

    source_engine = create_engine(source, pool_pre_ping=True)
    target_engine = create_engine(target, pool_pre_ping=True)
    try:
        with source_engine.connect() as src, target_engine.connect() as dst:
            # SELECT only; do not create missing source tables.
            source_rows, source_digest = snapshot(src)
            from sqlalchemy import inspect
            target_exists = inspect(dst).has_table(TABLE_NAME)
            if target_exists:
                target_rows, target_digest = snapshot(dst)
            else:
                target_rows, target_digest = [], None
        print(json.dumps({
            "mode": "preflight", "source_rows": len(source_rows),
            "source_sha256": source_digest, "target_table_exists": target_exists,
            "target_rows": len(target_rows), "target_sha256": target_digest,
            "match": target_exists and len(source_rows) == len(target_rows) and source_digest == target_digest,
        }, sort_keys=True))
        if args.check:
            return

        # Never merge or overwrite destination records. A nonempty destination
        # is valid only if it is already byte-for-byte equivalent.
        if target_rows:
            if len(source_rows) == len(target_rows) and source_digest == target_digest:
                print("Target already identical; no changes made")
                return
            raise ValueError("Destination already contains data: manual reconciliation is required")
        if target_exists and not source_rows:
            print("Both tables empty; no rows to migrate")
            return
        # Single transaction in destination; failure rolls back all row inserts.
        with target_engine.begin() as dst:
            meta.create_all(dst, checkfirst=True)
            target_count = dst.execute(select(func.count()).select_from(checklists)).scalar_one()
            if target_count != 0:
                raise ValueError("Target became nonempty; refusing an unsafe overwrite")
            for start in range(0, len(source_rows), 200):
                dst.execute(insert(checklists), source_rows[start:start + 200])
            copied_rows, copied_digest = snapshot(dst)
            if len(copied_rows) != len(source_rows) or copied_digest != source_digest:
                raise RuntimeError("Target checksum mismatch; rolling back new rows")
            # The environment flag is an operator assertion, not a database
            # lock. Re-read through a fresh transaction before committing any
            # target rows, so an intervening source edit cannot certify cutover.
            with source_engine.connect() as src:
                source_after, source_after_digest = snapshot(src)
            if len(source_after) != len(source_rows) or source_after_digest != source_digest:
                raise RuntimeError("Source changed during copy; rolling back new rows")
        print(json.dumps({
            "mode": "copied-and-verified", "rows": len(source_rows),
            "sha256": source_digest, "source_unchanged": True,
            "ready_for_manual_cutover": True,
        }, sort_keys=True))
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid leaking credentials from exception messages or connection strings.
        print("Migration stopped safely: " + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
