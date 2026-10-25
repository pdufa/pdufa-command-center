"""Read-only reconciliation package validation against immutable program identity keys.

Review-package composite keys are NOT registry source keys. Never infer a
regulatory application from a shared company, drug, indication, or NCT.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from urllib.parse import urlparse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

class ReviewItem(BaseModel):
    programKey: str = Field(min_length=1, max_length=512)
    status: str
    evidenceUrl: str
    reviewedOn: str
    notes: str = Field(default="", max_length=2000)
    exactSourceKey: str | None = Field(default=None, max_length=512)

class ReviewPackage(BaseModel):
    schemaVersion: int
    kind: str
    records: list[ReviewItem] = Field(max_length=10000)

def valid_review_source(value: str) -> bool:
    # Match the browser's explicit HTTPS authority form. Never silently trim
    # or reinterpret an evidence pointer supplied by an imported package.
    if not value.lower().startswith("https://") or any(ch.isspace() for ch in value) or "\\" in value:
        return False
    try:
        parsed = urlparse(value)
        port = parsed.port  # Invalid and out-of-range ports must be rejected.
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and "@" not in parsed.netloc and not parsed.username and not parsed.password
                and (port is None or 0 <= port <= 65535))
    except ValueError:
        return False

def valid_review_date(value: str, *, today: date | None = None) -> bool:
    try:
        day = date.fromisoformat(value)
        return day.isoformat() == value and day <= (today or datetime.now(timezone.utc).date())
    except ValueError:
        return False

def validate_review_package(payload: ReviewPackage, engine, identity_model):
    if payload.schemaVersion != 1 or payload.kind != "pdufa-reconciliation-review-export":
        raise ValueError("Unsupported review package schema")
    keys = {r.exactSourceKey for r in payload.records if r.exactSourceKey}
    with Session(engine) as session:
        known = set(session.scalars(select(identity_model.source_key).where(
            identity_model.source_key.in_(keys))).all()) if keys else set()
    results = []
    for row in payload.records:
        valid = (row.status in ("confirmed", "separate")
                 and valid_review_source(row.evidenceUrl) and valid_review_date(row.reviewedOn))
        # A composite UI key alone is insufficient to identify a backend application.
        outcome = ("INVALID_EVIDENCE" if not valid else
                   "EXACT_IDENTITY_MATCH" if row.exactSourceKey in known else
                   "UNMAPPED_EXACT_IDENTITY")
        results.append({"programKey": row.programKey,
                        "exactSourceKey": row.exactSourceKey,
                        "outcome": outcome})
    return {"mode": "READ_ONLY_NO_QUALIFICATION_CHANGES",
            "total": len(results),
            "exactMatches": sum(r["outcome"] == "EXACT_IDENTITY_MATCH" for r in results),
            "unmapped": sum(r["outcome"] == "UNMAPPED_EXACT_IDENTITY" for r in results),
            "invalid": sum(r["outcome"] == "INVALID_EVIDENCE" for r in results),
            "records": results}
