"""Read-only preflight joining blinded cohort and point-in-time evidence gates.

No outcome retrieval, scoring, predictions, persistence, or production imports.
"""
from __future__ import annotations

from typing import Any

from .blind_cohort import validate_blind_cohort
from .point_in_time_evidence import validate_point_in_time_evidence


def validate_historical_preflight(manifest: dict[str, Any], evidence_by_trial: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise TypeError("Manifest must be a dictionary")
    if not isinstance(evidence_by_trial, list):
        raise TypeError("Evidence records must be a list")
    cohort = validate_blind_cohort(manifest)
    errors = list(cohort["errors"])
    trials = manifest.get("trials")
    trials = trials if isinstance(trials, list) else []
    keys = set()
    for index, trial in enumerate(trials):
        if isinstance(trial, dict):
            key = (trial.get("nct_id"), trial.get("application_id"), trial.get("indication"))
            if all(isinstance(v, str) and v.strip() for v in key):
                keys.add(key)
    evidence_keys = set()
    for index, record in enumerate(evidence_by_trial):
        prefix = f"EVIDENCE_RECORD_{index}_"
        if not isinstance(record, dict):
            errors.append(prefix + "INVALID_RECORD")
            continue
        key = (record.get("nct_id"), record.get("application_id"), record.get("indication"))
        if not all(isinstance(v, str) and v.strip() for v in key):
            errors.append(prefix + "INVALID_LINKAGE")
            continue
        if key in evidence_keys:
            errors.append(prefix + "DUPLICATE_LINKAGE")
        evidence_keys.add(key)
        matches = [trial for trial in trials if isinstance(trial, dict) and
                   (trial.get("nct_id"), trial.get("application_id"), trial.get("indication")) == key]
        if len(matches) != 1:
            errors.append(prefix + "UNMATCHED_TRIAL")
            continue
        if record.get("cutoff_on") != matches[0].get("cutoff_on"):
            errors.append(prefix + "CUTOFF_MISMATCH")
        if any(field in record for field in ("fda_outcome", "actual_decision", "approval_status", "outcome_label")):
            errors.append(prefix + "OUTCOME_LEAKAGE")
        result = validate_point_in_time_evidence(record)
        errors.extend(prefix + error for error in result["errors"])
    if keys != evidence_keys:
        errors.append("INCOMPLETE_EVIDENCE_COVERAGE")
    return {
        "eligible_for_blind_review": not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
