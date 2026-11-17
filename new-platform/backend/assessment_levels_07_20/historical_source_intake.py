"""Fail-closed metadata intake for historical FDA evidence sources.

Validates source provenance and temporal eligibility before a document is
eligible for a frozen blind snapshot. No downloads, FDA outcomes or scoring.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from urllib.parse import urlsplit

_OUTCOME_KEYS = frozenset({"fda_outcome", "actual_decision", "approval_status",
                           "outcome_label", "fda_decision", "decision_result",
                           "approval_date"})
_SOURCE_TYPES = frozenset({"FDA", "CLINICALTRIALS_GOV", "SEC",
                           "SPONSOR_RELEASE", "PEER_REVIEWED",
                           "CONFERENCE_ABSTRACT", "SECONDARY_DISCOVERY"})


def _day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        result = date.fromisoformat(value)
    except ValueError:
        return None
    return result if result.isoformat() == value else None


def _contains_outcome(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in _OUTCOME_KEYS or _contains_outcome(v)
                   for key, v in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_outcome(v) for v in value)
    return False


def validate_historical_source_intake(
    records: list[dict[str, Any]], cutoff_on: str
) -> dict[str, Any]:
    if not isinstance(records, list):
        raise TypeError("Source intake records must be a list")
    cutoff = _day(cutoff_on)
    if cutoff is None:
        raise ValueError("cutoff_on must be an ISO date")
    errors: list[str] = []
    if not records:
        errors.append("MISSING_SOURCES")
    seen: set[tuple[str, str, str, str]] = set()
    for index, record in enumerate(records):
        prefix = f"SOURCE_{index}_"
        if not isinstance(record, dict):
            errors.append(prefix + "INVALID_RECORD")
            continue
        if _contains_outcome(record):
            errors.append(prefix + "OUTCOME_LEAKAGE")
        for field in ("nct_id", "application_id", "indication"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                errors.append(prefix + "MISSING_" + field.upper())
        kind = record.get("source_type")
        if kind not in _SOURCE_TYPES:
            errors.append(prefix + "INVALID_SOURCE_TYPE")
        url = record.get("source_url")
        if not isinstance(url, str):
            errors.append(prefix + "INVALID_SOURCE_URL")
        else:
            parsed = urlsplit(url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                errors.append(prefix + "INVALID_SOURCE_URL")
        digest = record.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            errors.append(prefix + "INVALID_SHA256")
        published = _day(record.get("published_on"))
        retrieved = _day(record.get("retrieved_on"))
        if published is None or retrieved is None:
            errors.append(prefix + "INVALID_DATES")
        elif not (published <= retrieved < cutoff):
            errors.append(prefix + "TEMPORAL_LEAKAGE")
        if kind == "SECONDARY_DISCOVERY":
            errors.append(prefix + "SECONDARY_SOURCE_NOT_PRIMARY_EVIDENCE")
        if all(isinstance(record.get(k), str) for k in ("nct_id", "application_id", "indication", "source_url")):
            key = tuple(record[k] for k in ("nct_id", "application_id", "indication", "source_url"))
            if key in seen:
                errors.append(prefix + "DUPLICATE_SOURCE")
            seen.add(key)
    return {
        "eligible_for_frozen_evidence": not errors,
        "source_count": len(records),
        "scientific_status": "NOT_VERIFIED",
        "accuracy_evaluated": False,
        "errors": sorted(set(errors)),
    }
