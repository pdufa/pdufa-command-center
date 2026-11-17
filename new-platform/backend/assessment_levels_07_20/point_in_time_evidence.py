"""Conservative point-in-time evidence gate for isolated Levels 7–20.

This is a provenance check, not a scientific score or FDA prediction.
All dates are calendar dates; evidence on the cutoff day is conservatively
excluded unless an independent timestamp-level gate is implemented.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlsplit


def _parse_day(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        day = date.fromisoformat(value)
    except ValueError:
        return None
    return day if day.isoformat() == value else None


def validate_point_in_time_evidence(record: dict[str, Any]) -> dict[str, Any]:
    """Reject incomplete, post-cutoff, or temporally ambiguous evidence."""
    if not isinstance(record, dict):
        raise TypeError("Evidence record must be a dictionary")
    errors: list[str] = []
    cutoff = _parse_day(record.get("cutoff_on"))
    if cutoff is None:
        errors.append("INVALID_CUTOFF")
    evidence = record.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        errors.append("MISSING_EVIDENCE")
        evidence = []
    for index, item in enumerate(evidence):
        prefix = f"EVIDENCE_{index}_"
        if not isinstance(item, dict):
            errors.append(prefix + "INVALID_ITEM")
            continue
        url = item.get("source_url")
        if not isinstance(url, str):
            errors.append(prefix + "INVALID_SOURCE")
        else:
            try:
                parsed = urlsplit(url)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                    errors.append(prefix + "INVALID_SOURCE")
            except ValueError:
                errors.append(prefix + "INVALID_SOURCE")
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
            errors.append(prefix + "INVALID_HASH")
        if any(k in item for k in ("fda_outcome", "actual_decision", "approval_status", "outcome_label")):
            errors.append(prefix + "OUTCOME_LEAKAGE")
        published = _parse_day(item.get("published_on"))
        retrieved = _parse_day(item.get("retrieved_on"))
        if published is not None and retrieved is not None and published > retrieved:
            errors.append(prefix + "PUBLISHED_AFTER_RETRIEVAL")
        for field in ("published_on", "retrieved_on"):
            day = _parse_day(item.get(field))
            if day is None:
                errors.append(prefix + "INVALID_" + field.upper())
            elif cutoff is not None and day >= cutoff:
                errors.append(prefix + "NOT_BEFORE_CUTOFF_" + field.upper())
        if not isinstance(item.get("nct_id"), str) or item["nct_id"] != record.get("nct_id"):
            errors.append(prefix + "TRIAL_MISMATCH")
    return {
        "eligible_for_owner_review": not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
