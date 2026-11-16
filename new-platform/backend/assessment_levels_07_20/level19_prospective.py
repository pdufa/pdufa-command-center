"""Isolated Level 19 prospective prediction/calibration eligibility gate.

No fitting, probabilities, model inference, or production writes. A prospective
freeze must predate outcomes; retrospective reconstructions are not blind.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")


def _instant(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def validate_level19_prospective(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "input_snapshot_id", "input_digest",
                "model_artifact_id", "model_version", "frozen_at",
                "first_outcome_available_at", "evaluation_cohort_id")
    missing = sorted(k for k in required if not record.get(k))
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    for field in ("input_snapshot_id", "input_digest", "model_artifact_id",
                  "model_version", "evaluation_cohort_id"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append("INVALID_" + field.upper())
    freeze = _instant(record.get("frozen_at"))
    outcome = _instant(record.get("first_outcome_available_at"))
    if freeze is None or outcome is None:
        errors.append("INVALID_UTC_CHRONOLOGY")
    elif freeze >= outcome:
        errors.append("NOT_PROSPECTIVE_FREEZE")
    if record.get("outcome_exposed_at_freeze") is not False:
        errors.append("OUTCOME_EXPOSURE_NOT_EXCLUDED")
    if record.get("inputs_immutable_verified") is not True:
        errors.append("IMMUTABLE_INPUTS_NOT_VERIFIED")
    if record.get("model_frozen_before_outcomes") is not True:
        errors.append("MODEL_FREEZE_NOT_VERIFIED")
    if record.get("out_of_sample_cohort_verified") is not True:
        errors.append("OUT_OF_SAMPLE_COHORT_NOT_VERIFIED")
    if record.get("calibration_metrics_verified") is not True:
        errors.append("CALIBRATION_NOT_VERIFIED")
    return {
        "level": 19, "engine": "isolated-level19-prospective-gate-v1",
        "eligible_for_calibration_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None, "fda_prediction": "ABSTAIN",
        "missing_fields": missing, "errors": sorted(set(errors)),
    }
