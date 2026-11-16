"""Fail-closed offline validator for a pre-unblinding prediction ledger.

This checks provenance and chronology only. It never produces predictions,
accesses FDA outcomes, or asserts calibration/accuracy.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_HASH = re.compile(r"[0-9a-f]{64}\\Z")
_NCT = re.compile(r"NCT[0-9]{8}\\Z")
_OUTCOMES = frozenset({"fda_outcome", "actual_decision", "approval_status",
                       "outcome_label", "fda_decision", "decision_result", "approval_date"})


def _day(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _leaks(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in _OUTCOMES or _leaks(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_leaks(child) for child in value)
    return False


def validate_prediction_ledger(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(records, list):
        raise TypeError("Prediction ledger must be a list")
    errors: list[str] = []
    if not records:
        errors.append("MISSING_RECORDS")
    seen: set[tuple[str, str, str, int]] = set()
    for index, record in enumerate(records):
        prefix = f"RECORD_{index}_"
        if not isinstance(record, dict):
            errors.append(prefix + "INVALID_RECORD")
            continue
        if _leaks(record):
            errors.append(prefix + "OUTCOME_LEAKAGE")
        nct = record.get("nct_id")
        application = record.get("application_id")
        indication = record.get("indication")
        level = record.get("level")
        if not isinstance(nct, str) or not _NCT.fullmatch(nct):
            errors.append(prefix + "INVALID_NCT")
        if not isinstance(application, str) or not application.strip():
            errors.append(prefix + "INVALID_APPLICATION")
        if not isinstance(indication, str) or not indication.strip():
            errors.append(prefix + "INVALID_INDICATION")
        if type(level) is not int or not 7 <= level <= 20:
            errors.append(prefix + "INVALID_LEVEL")
        if isinstance(nct, str) and isinstance(application, str) and isinstance(indication, str) and type(level) is int:
            key = (nct, application, indication, level)
            if key in seen:
                errors.append(prefix + "DUPLICATE_EVENT_LEVEL")
            seen.add(key)
        frozen = _day(record.get("frozen_on"))
        cutoff = _day(record.get("cutoff_on"))
        decision = _day(record.get("decision_on"))
        predicted = _day(record.get("predicted_on"))
        if any(day is None for day in (frozen, cutoff, decision, predicted)):
            errors.append(prefix + "INVALID_DATES")
        elif not (frozen <= predicted < cutoff < decision):
            errors.append(prefix + "TEMPORAL_LEAKAGE")
        for field in ("snapshot_sha256", "prediction_sha256"):
            digest = record.get(field)
            if not isinstance(digest, str) or not _HASH.fullmatch(digest):
                errors.append(prefix + "INVALID_" + field.upper())
        if record.get("prediction") not in ("APPROVE", "NOT_APPROVE", "ABSTAIN"):
            errors.append(prefix + "INVALID_PREDICTION")
        if record.get("prediction") != "ABSTAIN" and record.get("scientific_status") != "VERIFIED":
            errors.append(prefix + "UNVERIFIED_PREDICTION")
    return {
        "ledger_ready_for_independent_review": not errors,
        "record_count": len(records),
        "accuracy_evaluated": False,
        "errors": sorted(set(errors)),
    }
