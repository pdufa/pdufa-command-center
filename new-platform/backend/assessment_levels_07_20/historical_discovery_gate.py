"""Fail-closed gate for public historical discovery records.

Discovery leads are never eligible for blinded evaluation merely because their
publication dates precede an FDA decision. This module is offline and read-only.
"""
from __future__ import annotations

from typing import Any


def inspect_discovery_records(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise TypeError("Discovery payload must be a dict")
    events = payload.get("events")
    errors: list[str] = []
    if payload.get("status") != "DISCOVERY_ONLY":
        errors.append("DISCOVERY_STATUS_REQUIRED")
    if payload.get("blind_eligible") is not False:
        errors.append("BLIND_ELIGIBILITY_MUST_BE_FALSE")
    if payload.get("source_bytes_verified") is not False:
        errors.append("UNVERIFIED_BYTES_MUST_NOT_BE_CLAIMED_VERIFIED")
    if not isinstance(events, list) or not events:
        errors.append("EVENTS_REQUIRED")
        events = []
    source_count = 0
    quarantined = 0
    for event_index, event in enumerate(events):
        if not isinstance(event, dict):
            errors.append(f"EVENT_{event_index}_INVALID")
            continue
        for field in ("nct_id", "application_id", "indication"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                errors.append(f"EVENT_{event_index}_MISSING_{field.upper()}")
        sources = event.get("sources")
        if not isinstance(sources, list):
            errors.append(f"EVENT_{event_index}_SOURCES_INVALID")
            continue
        for source_index, source in enumerate(sources):
            source_count += 1
            if not isinstance(source, dict):
                errors.append(f"EVENT_{event_index}_SOURCE_{source_index}_INVALID")
                continue
            if source.get("verified_historical_bytes") is not False:
                errors.append(f"EVENT_{event_index}_SOURCE_{source_index}_BYTES_UNVERIFIED")
            if source.get("outcome_exposing") is True:
                quarantined += 1
                if source.get("quarantine") != "OUTCOME_ONLY":
                    errors.append(f"EVENT_{event_index}_SOURCE_{source_index}_OUTCOME_NOT_QUARANTINED")
    return {
        "discovery_record_valid": not errors,
        "blind_eligible": False,
        "source_bytes_verified": False,
        "event_count": len(events),
        "source_count": source_count,
        "outcome_quarantined_count": quarantined,
        "accuracy_evaluated": False,
        "errors": errors,
    }
