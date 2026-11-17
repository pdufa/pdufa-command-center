"""Fail-closed manifest validation for blinded historical PDUFA evaluation.

This checks frozen cohort metadata only; it neither reads outcomes nor scores trials.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


_OUTCOME_KEYS = frozenset({
    "fda_outcome", "actual_decision", "approval_status", "outcome_label",
    "fda_decision", "decision_result", "approval_date",
})


def _contains_outcome_fields(value: Any) -> bool:
    if isinstance(value, dict):
        return any(key in _OUTCOME_KEYS or _contains_outcome_fields(child)
                   for key, child in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_outcome_fields(child) for child in value)
    return False


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def validate_blind_cohort(manifest: dict[str, Any]) -> dict[str, Any]:
    """Require immutable, uniquely keyed, pre-decision trial snapshots."""
    if not isinstance(manifest, dict):
        raise TypeError("Cohort manifest must be a dictionary")
    errors: list[str] = []
    if any(key in _OUTCOME_KEYS or _contains_outcome_fields(value) for key, value in manifest.items() if key != "trials"):
        errors.append("MANIFEST_OUTCOME_LEAKAGE")
    trials = manifest.get("trials")
    if not isinstance(trials, list) or not trials:
        errors.append("MISSING_TRIALS")
        trials = []
    seen: set[tuple[str, str, str]] = set()
    for index, trial in enumerate(trials):
        prefix = f"TRIAL_{index}_"
        if not isinstance(trial, dict):
            errors.append(prefix + "INVALID_RECORD")
            continue
        nct = trial.get("nct_id")
        application = trial.get("application_id")
        indication = trial.get("indication")
        if not isinstance(nct, str) or not _NCT.fullmatch(nct):
            errors.append(prefix + "INVALID_NCT")
        if not isinstance(application, str) or not application.strip():
            errors.append(prefix + "MISSING_APPLICATION")
        if not isinstance(indication, str) or not indication.strip():
            errors.append(prefix + "MISSING_INDICATION")
        if all(isinstance(x, str) and x.strip() for x in (nct, application, indication)):
            key = (nct, application, indication)
            if key in seen:
                errors.append(prefix + "DUPLICATE_EVENT")
            seen.add(key)
        cutoff = _day(trial.get("cutoff_on"))
        decision = _day(trial.get("decision_on"))
        frozen = _day(trial.get("frozen_on"))
        if not cutoff or not decision or not frozen:
            errors.append(prefix + "INVALID_DATES")
        elif not (frozen < cutoff < decision):
            errors.append(prefix + "TEMPORAL_LEAKAGE")
        if not isinstance(trial.get("snapshot_sha256"), str) or not _HASH.fullmatch(trial["snapshot_sha256"]):
            errors.append(prefix + "INVALID_SNAPSHOT_HASH")
        # Outcome fields must never be available in a blind feature manifest.
        if _contains_outcome_fields(trial):
            errors.append(prefix + "OUTCOME_LEAKAGE")
    return {
        "eligible_for_blind_review": not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
