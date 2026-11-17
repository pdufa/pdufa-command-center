"""Read-only coverage report for an isolated blinded historical cohort.

Does not fetch external records, persist data, calculate accuracy, or predict outcomes.
"""
from __future__ import annotations

from typing import Any

from .historical_preflight import validate_historical_preflight


def summarize_historical_coverage(manifest: dict[str, Any], evidence_by_trial: list[dict[str, Any]]) -> dict[str, Any]:
    preflight = validate_historical_preflight(manifest, evidence_by_trial)
    trials = manifest.get("trials", [])
    trials = trials if isinstance(trials, list) else []
    valid_trials = [trial for trial in trials if isinstance(trial, dict)]
    records = [record for record in evidence_by_trial if isinstance(record, dict)]
    def key(record: dict[str, Any]) -> tuple[Any, Any, Any]:
        return record.get("nct_id"), record.get("application_id"), record.get("indication")
    trial_keys = {key(trial) for trial in valid_trials}
    evidence_keys = {key(record) for record in records}
    missing = trial_keys - evidence_keys
    unlinked = evidence_keys - trial_keys
    return {
        "trial_count": len(trials),
        "evidence_record_count": len(evidence_by_trial),
        "trials_with_evidence_count": sum(1 for trial in valid_trials if key(trial) in evidence_keys),
        "missing_evidence_count": len(missing),
        "unlinked_evidence_count": len(unlinked),
        "eligible_for_blind_review": preflight["eligible_for_blind_review"],
        "errors": preflight["errors"],
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "accuracy": None,
    }
