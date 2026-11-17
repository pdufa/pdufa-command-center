"""Read-only blind evaluation gate: no accuracy metrics without adjudicated labels.

Deliberately does not compute model accuracy or inspect hidden outcomes.
"""
from __future__ import annotations

from typing import Any


def validate_evaluation_readiness(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("Evaluation readiness input must be a dictionary")
    errors: list[str] = []
    required = ("frozen_manifest_sha256", "prediction_artifact_sha256",
                "outcome_adjudication_sha256", "protocol_version")
    for field in required:
        value = record.get(field)
        if field.endswith("_sha256"):
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                errors.append("INVALID_" + field.upper())
        elif not isinstance(value, str) or not value.strip():
            errors.append("MISSING_" + field.upper())
    if record.get("predictions_frozen_before_unblinding") is not True:
        errors.append("PREDICTIONS_NOT_FROZEN")
    if record.get("outcomes_independently_adjudicated") is not True:
        errors.append("OUTCOMES_NOT_ADJUDICATED")
    if record.get("evaluation_protocol_preregistered") is not True:
        errors.append("PROTOCOL_NOT_PREREGISTERED")
    if record.get("evaluation_approved_by_owner") is not True:
        errors.append("OWNER_APPROVAL_REQUIRED")
    return {
        "ready_for_separate_evaluation": not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "accuracy": None,
        "errors": sorted(set(errors)),
    }
