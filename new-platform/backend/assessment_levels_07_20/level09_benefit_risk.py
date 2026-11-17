"""Isolated Level 9 benefit-risk evidence readiness, not benefit-risk scoring.

Requires reviewed indication-specific efficacy, harms and population assessments
from Levels 3-5 and 7-8. No weighted substitute or invented FDA probability.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_DEPENDENCIES = (3, 4, 5, 7, 8)


def validate_level9_benefit_risk(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "indication", "population", "cutoff_on", "dependencies",
                "benefit_harm_interpretation", "reviewer_id")
    missing = sorted(key for key in required if not record.get(key))
    nct = record.get("nct_id")
    if not isinstance(nct, str) or not _NCT.fullmatch(nct):
        errors.append("INVALID_EXACT_NCT")
    for key in ("indication", "population", "reviewer_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append("INVALID_" + key.upper())
    try:
        cutoff = date.fromisoformat(record["cutoff_on"])
    except (KeyError, ValueError, TypeError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    dependencies = record.get("dependencies")
    if not isinstance(dependencies, dict):
        dependencies = {}
        errors.append("MISSING_DEPENDENCY_MAP")
    for level in _DEPENDENCIES:
        item = dependencies.get(str(level))
        if not isinstance(item, dict):
            errors.append(f"MISSING_LEVEL_{level}_REVIEW")
            continue
        if item.get("scientific_status") != "VERIFIED":
            errors.append(f"UNVERIFIED_LEVEL_{level}")
        if item.get("nct_id") != nct or item.get("indication") != record.get("indication"):
            errors.append(f"LEVEL_{level}_IDENTITY_MISMATCH")
        if item.get("population") != record.get("population"):
            errors.append(f"LEVEL_{level}_POPULATION_MISMATCH")
        if not isinstance(item.get("immutable_review_id"), str) or not item["immutable_review_id"].strip():
            errors.append(f"MISSING_LEVEL_{level}_REVIEW_ID")
        try:
            reviewed_on = date.fromisoformat(item["reviewed_on"])
            if cutoff and reviewed_on > cutoff:
                errors.append(f"POST_CUTOFF_LEVEL_{level}_REVIEW")
        except (KeyError, ValueError, TypeError):
            errors.append(f"INVALID_LEVEL_{level}_REVIEW_DATE")
    interpretation = record.get("benefit_harm_interpretation")
    if not isinstance(interpretation, dict):
        errors.append("MISSING_BENEFIT_HARM_INTERPRETATION")
    else:
        for field in ("benefit_magnitude", "harm_magnitude", "clinical_tradeoff",
                      "uncertainty", "source_grounded_rationale"):
            if not isinstance(interpretation.get(field), str) or not interpretation[field].strip():
                errors.append("MISSING_INTERPRETATION_" + field.upper())
    if record.get("arbitrary_weighted_score") is not None:
        errors.append("ARBITRARY_WEIGHTED_SCORE_FORBIDDEN")
    return {
        "level": 9, "engine": "isolated-level9-benefit-risk-readiness-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
