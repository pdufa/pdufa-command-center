"""One irreversible identity per exact original Pipeline key.

PDUFA numbers are allocated by the persistent Neon sequence. They are never
computed from a sorted source list or recycled after removal/promotion/re-entry.
This module deliberately does not call Streamlit, scanners, or brokers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from .main import ENGINE, ProgramIdentity

PREFIX = "PDUFA-"


def number_workspace(source: dict) -> dict:
    # Build from the canonical exact source key, NOT ticker or stage.
    # Include historical IDs so archived candidates never lose their number.
    identity: dict[str, tuple[str, str]] = {}
    for row in source.get("pipeline", []):
        key = row.get("id")
        if isinstance(key, str) and key.startswith(("APPLICATION|", "TRIAL|")):
            identity.setdefault(key, (str(row.get("ticker") or ""), str(row.get("drug") or "")))
    for category in ("GEM_JR", "GEM"):
        stage = source.get("members", {}).get(category, {})
        for row in list(stage.get("rows", [])) + list(stage.get("history", [])):
            key = row.get("id")
            if isinstance(key, str) and key.startswith(("APPLICATION|", "TRIAL|")):
                identity.setdefault(key, (str(row.get("ticker") or ""), str(row.get("drug") or "")))
    if not identity:
        raise ValueError("No valid exact program identities available")
    now = datetime.now(timezone.utc)
    # Serialize initial ID allocation against concurrent requests using an
    # atomic database conflict-safe insert; unique source keys never change.
    with Session(ENGINE) as session:
        keys = sorted(identity)
        dialect = session.bind.dialect.name
        if dialect == "postgresql":
            insert_stmt = postgres_insert
        elif dialect == "sqlite":
            insert_stmt = sqlite_insert
        else:
            raise RuntimeError("Unsupported identity registry dialect")
        result = {}
        for offset in range(0, len(keys), 1000):
            for key, serial in session.execute(
                select(ProgramIdentity.source_key, ProgramIdentity.id)
                .where(ProgramIdentity.source_key.in_(keys[offset:offset + 1000]))
            ):
                result[key] = f"{PREFIX}{serial:06d}"
        missing = [key for key in keys if key not in result]
        for offset in range(0, len(missing), 300):
            chunk = missing[offset:offset + 300]
            values = [
                {"source_key": key, "ticker": identity[key][0][:15],
                 "drug": identity[key][1][:300], "created_at": now}
                for key in chunk
            ]
            session.execute(insert_stmt(ProgramIdentity).values(values).on_conflict_do_nothing(
                index_elements=["source_key"],
            ))
        if missing:
            session.commit()
            for offset in range(0, len(missing), 1000):
                for key, serial in session.execute(
                    select(ProgramIdentity.source_key, ProgramIdentity.id)
                    .where(ProgramIdentity.source_key.in_(missing[offset:offset + 1000]))
                ):
                    result[key] = f"{PREFIX}{serial:06d}"
    if len(result) != len(identity):
        raise RuntimeError("Permanent program registry incomplete")
    # Keep the original source cache immutable. Never give two program stages
    # different numbers for the same exact trial/application key.
    snapshot = {
        **source,
        "pipeline": [{**r, "programId": result.get(r.get("id"))} for r in source["pipeline"]],
        "members": {
            name: {
                **detail,
                "rows": [{**r, "programId": result.get(r.get("id"))} for r in detail.get("rows", [])],
                "history": [{**r, "programId": result.get(r.get("id"))} for r in detail.get("history", [])],
            }
            for name, detail in source.get("members", {}).items()
        },
        "identityRegistry": {
            "format": "PDUFA-000001",
            "strategy": "Neon database persistent sequence / never recycled",
            "registeredExactPrograms": len(result),
        },
    }
    return snapshot
