"""One-time, non-destructive, in-network checklist migration from Render to Neon.

This is invoked on service startup ONLY when PDUFA_MIGRATION_COPY_ON_BOOT=1
and PDUFA_MIGRATION_READ_ONLY=1. The source database is never modified.
Successful transfer is verified by count and canonical record SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _normalized_url(value: str) -> str:
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


def _snapshot(engine, model):
    with Session(engine) as session:
        records = [
            {
                "ticker": item.ticker,
                "stage": item.stage,
                "selections": item.selections,
                "notes": item.notes,
                "version": item.version,
                "updated_at": item.updated_at,
            }
            for item in session.scalars(
                select(model).order_by(model.ticker, model.stage)
            )
        ]
    data = hashlib.sha256()
    for record in records:
        canonical = {
            **record,
            "updated_at": record["updated_at"].astimezone(
                __import__("datetime").timezone.utc
            ).isoformat() if isinstance(record["updated_at"], datetime) and
            record["updated_at"].tzinfo is not None else str(record["updated_at"]),
        }
        data.update(json.dumps(
            canonical, sort_keys=True, ensure_ascii=False,
            separators=(",", ":"), default=str,
        ).encode("utf-8"))
        data.update(b"\n")
    return records, data.hexdigest()


def copy_with_checks(source_engine, target_url, base, checklist_model):
    if os.getenv("PDUFA_MIGRATION_READ_ONLY", "").strip().lower() not in ("1", "true", "yes"):
        raise RuntimeError("Write freeze must be enabled before database copy")
    if os.getenv("PDUFA_REQUIRE_POSTGRES", "").strip().lower() not in ("1", "true", "yes"):
        raise RuntimeError("Production PostgreSQL must be required")
    target_url = _normalized_url(target_url)
    if not target_url.startswith("postgresql+psycopg://"):
        raise ValueError("Migration target must be PostgreSQL")
    source_url = source_engine.url
    dest_url = make_url(target_url)
    if ((source_url.host or "").lower(), source_url.port or 5432, source_url.database) == (
        (dest_url.host or "").lower(), dest_url.port or 5432, dest_url.database
    ):
        raise ValueError("Source and target databases must differ")
    target_engine = create_engine(target_url, pool_pre_ping=True)
    try:
        source_rows, source_digest = _snapshot(source_engine, checklist_model)
        base.metadata.create_all(bind=target_engine)
        target_rows, target_digest = _snapshot(target_engine, checklist_model)
        if target_rows and (source_digest != target_digest or len(source_rows) != len(target_rows)):
            raise ValueError("Target database is nonempty and differs; refusing overwrite")
        if not target_rows and source_rows:
            with Session(target_engine) as dest:
                if dest.scalar(select(__import__("sqlalchemy").func.count()).select_from(checklist_model)) != 0:
                    raise ValueError("Target changed during copy; refusing overwrite")
                dest.add_all([checklist_model(**item) for item in source_rows])
                dest.commit()
        post_rows, post_digest = _snapshot(target_engine, checklist_model)
        # An independent second pass on source catches intervening writes if
        # the read-only flag wasn't actually enforced by an earlier deploy.
        source_after, source_after_digest = _snapshot(source_engine, checklist_model)
        if (len(source_rows) != len(post_rows) or source_digest != post_digest
                or len(source_rows) != len(source_after)
                or source_after_digest != source_digest):
            raise RuntimeError("Record count/digest changed during migration; do not switch")
        logger.warning(
            "PDUFA_DATABASE_COPY_VERIFIED source_rows=%d target_rows=%d sha256=%s",
            len(source_rows), len(post_rows), post_digest,
        )
    finally:
        target_engine.dispose()
