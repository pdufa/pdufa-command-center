"""Offline, outcome-blind join of historical evidence and prediction ledger.

No outcomes, scoring, or database access. A valid join is not a scientific
validation or an accuracy result.
"""
from __future__ import annotations

from typing import Any

from .historical_preflight import validate_historical_preflight
from .prediction_ledger import validate_prediction_ledger


def validate_blind_prediction_package(
    manifest: dict[str, Any], evidence: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
) -> dict[str, Any]:
    preflight = validate_historical_preflight(manifest, evidence)
    ledger = validate_prediction_ledger(predictions)
    errors = ["PREFLIGHT_" + e for e in preflight["errors"]]
    errors += ["LEDGER_" + e for e in ledger["errors"]]
    trials = manifest.get("trials", [])
    trials = trials if isinstance(trials, list) else []
    expected = {}
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            continue
        key = (trial.get("nct_id"), trial.get("application_id"), trial.get("indication"))
        if key in expected:
            errors.append("DUPLICATE_MANIFEST_EVENT")
        expected[key] = trial
    covered = set()
    for index, prediction in enumerate(predictions):
        if not isinstance(prediction, dict):
            continue
        prefix = f"PREDICTION_{index}_"
        key = (prediction.get("nct_id"), prediction.get("application_id"), prediction.get("indication"))
        if key not in expected:
            errors.append(prefix + "UNMATCHED_EVENT")
            continue
        covered.add(key)
        trial = expected[key]
        for field in ("frozen_on", "cutoff_on", "decision_on", "snapshot_sha256"):
            if prediction.get(field) != trial.get(field):
                errors.append(prefix + "MANIFEST_" + field.upper() + "_MISMATCH")
    if set(expected) != covered:
        errors.append("INCOMPLETE_PREDICTION_COVERAGE")
    return {
        "ready_for_independent_blind_review": not errors,
        "historical_trial_count": len(trials),
        "prediction_record_count": len(predictions),
        "accuracy_evaluated": False,
        "scientific_status": "NOT_VERIFIED",
        "errors": sorted(set(errors)),
    }
