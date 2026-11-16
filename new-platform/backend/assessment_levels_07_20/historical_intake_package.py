"""Offline join of source intake and frozen blind historical package.

The source intake is a prerequisite for review readiness. It does not
substitute for evidence bytes or scientific assessment.
"""
from __future__ import annotations

from typing import Any

from .frozen_blind_package import validate_frozen_blind_package
from .historical_source_intake import validate_historical_source_intake


def validate_historical_intake_package(
    manifest: dict[str, Any],
    evidence: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    snapshot_artifacts: list[dict[str, Any]],
    source_records: list[dict[str, Any]],
) -> dict[str, Any]:
    frozen = validate_frozen_blind_package(
        manifest, evidence, predictions, snapshot_artifacts
    )
    errors = ["FROZEN_" + error for error in frozen["errors"]]
    trials = manifest.get("trials", [])
    trials = trials if isinstance(trials, list) else []
    expected = {
        (trial.get("nct_id"), trial.get("application_id"), trial.get("indication")): trial
        for trial in trials if isinstance(trial, dict)
    }
    grouped: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for index, record in enumerate(source_records):
        if not isinstance(record, dict):
            errors.append(f"SOURCE_{index}_INVALID_RECORD")
            continue
        key = (record.get("nct_id"), record.get("application_id"), record.get("indication"))
        if key not in expected:
            errors.append(f"SOURCE_{index}_UNMATCHED_EVENT")
            continue
        grouped.setdefault(key, []).append(record)
    for index, (key, trial) in enumerate(expected.items()):
        prefix = f"TRIAL_{index}_"
        if key not in grouped:
            errors.append(prefix + "MISSING_SOURCE_INTAKE")
            continue
        cutoff = trial.get("cutoff_on")
        try:
            result = validate_historical_source_intake(grouped[key], cutoff)
        except ValueError:
            errors.append(prefix + "INVALID_CUTOFF")
            continue
        errors.extend(prefix + error for error in result["errors"])
    return {
        "ready_for_independent_blind_review": not errors,
        "historical_trial_count": frozen["historical_trial_count"],
        "source_record_count": len(source_records),
        "accuracy_evaluated": False,
        "scientific_status": "NOT_VERIFIED",
        "errors": sorted(set(errors)),
    }
