"""Bind frozen trial snapshot hashes to supplied immutable bytes.

This is a pure offline integrity gate, not a scientific assessment.
"""
from __future__ import annotations

from typing import Any

from .blind_cohort import validate_blind_cohort
from .frozen_artifacts import verify_frozen_artifacts


def verify_cohort_snapshots(manifest: dict[str, Any], artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    cohort = validate_blind_cohort(manifest)
    integrity = verify_frozen_artifacts(artifacts)
    errors = list(cohort["errors"]) + list(integrity["errors"])
    trials = manifest.get("trials", [])
    trials = trials if isinstance(trials, list) else []
    expected = {}
    for index, trial in enumerate(trials):
        if not isinstance(trial, dict):
            continue
        identifier = trial.get("snapshot_artifact_id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"TRIAL_{index}_MISSING_SNAPSHOT_ARTIFACT_ID")
            continue
        if identifier in expected:
            errors.append(f"TRIAL_{index}_DUPLICATE_SNAPSHOT_ARTIFACT_ID")
        expected[identifier] = trial.get("snapshot_sha256")
    actual = {}
    for index, artifact in enumerate(artifacts):
        if isinstance(artifact, dict) and isinstance(artifact.get("artifact_id"), str):
            actual[artifact["artifact_id"]] = artifact.get("sha256")
    for identifier, digest in expected.items():
        if identifier not in actual:
            errors.append("MISSING_LINKED_SNAPSHOT")
        elif actual[identifier] != digest:
            errors.append("SNAPSHOT_MANIFEST_HASH_MISMATCH")
    if set(actual) != set(expected):
        errors.append("SNAPSHOT_ARTIFACT_SET_MISMATCH")
    return {
        "snapshots_verified": not errors,
        "trial_count": len(trials),
        "artifact_count": len(artifacts),
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
