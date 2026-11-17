"""Read-only integrity gate for a complete blind historical review package.

Combines pre-cutoff evidence checks, frozen snapshot byte verification, and
prediction-ledger linkage. No outcomes, predictions, or accuracy calculations.
"""
from __future__ import annotations

from typing import Any

from .blind_prediction_package import validate_blind_prediction_package
from .cohort_snapshot_integrity import verify_cohort_snapshots


def validate_frozen_blind_package(
    manifest: dict[str, Any],
    evidence: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    snapshot_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    joined = validate_blind_prediction_package(manifest, evidence, predictions)
    snapshots = verify_cohort_snapshots(manifest, snapshot_artifacts)
    errors = ["JOIN_" + e for e in joined["errors"]]
    errors.extend("SNAPSHOT_" + e for e in snapshots["errors"])
    return {
        "ready_for_independent_blind_review": not errors,
        "historical_trial_count": joined["historical_trial_count"],
        "prediction_record_count": joined["prediction_record_count"],
        "snapshot_artifact_count": snapshots["artifact_count"],
        "accuracy_evaluated": False,
        "scientific_status": "NOT_VERIFIED",
        "errors": sorted(set(errors)),
    }
