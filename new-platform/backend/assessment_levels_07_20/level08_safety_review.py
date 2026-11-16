"""Isolated Level 8 person-time and safety evidence review gate."""
from __future__ import annotations
from datetime import date
import math
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_CRITERIA = ("event_ascertainment", "exposure_comparability", "censoring_followup",
             "discontinuation_review", "serious_event_pattern", "clinical_safety_interpretation")


def validate_level8_review(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    nct = record.get("nct_id")
    if not isinstance(nct, str) or not _NCT.fullmatch(nct):
        errors.append("INVALID_NCT")
    if not isinstance(record.get("population"), str) or not record["population"].strip():
        errors.append("MISSING_POPULATION")
    try:
        cutoff = date.fromisoformat(record["cutoff_on"])
    except (KeyError, TypeError, ValueError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    if record.get("exposure_unit") not in ("PERSON_YEARS", "PERSON_MONTHS"):
        errors.append("INVALID_EXPOSURE_UNIT")
    for arm in ("treatment", "comparator"):
        item = record.get(arm)
        if arm == "comparator" and item is None and record.get("single_arm") is True:
            continue
        if not isinstance(item, dict):
            errors.append("MISSING_" + arm.upper())
            continue
        events, exposure = item.get("events"), item.get("person_time")
        if type(events) is not int or events < 0 or type(exposure) not in (int, float) or not math.isfinite(exposure) or exposure <= 0:
            errors.append("INVALID_" + arm.upper() + "_EVENTS_OR_PERSON_TIME")
        if item.get("nct_id") != nct:
            errors.append("WRONG_TRIAL_" + arm.upper())
    for criterion in _CRITERIA:
        review = record.get(criterion)
        if not isinstance(review, dict) or review.get("status") != "REVIEWED":
            errors.append("UNREVIEWED_" + criterion.upper())
            continue
        if review.get("nct_id") != nct:
            errors.append("WRONG_TRIAL_" + criterion.upper())
        if not isinstance(review.get("source_url"), str) or not review["source_url"].startswith("https://"):
            errors.append("MISSING_SOURCE_" + criterion.upper())
        if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
            errors.append("MISSING_RATIONALE_" + criterion.upper())
        try:
            if cutoff and date.fromisoformat(review["reviewed_on"]) > cutoff:
                errors.append("POST_CUTOFF_" + criterion.upper())
        except (KeyError, TypeError, ValueError):
            errors.append("INVALID_REVIEW_DATE_" + criterion.upper())
    if record.get("count_model") not in (None, "INDEPENDENT_POISSON_COUNTS"):
        errors.append("UNSUPPORTED_COUNT_MODEL")
    if record.get("count_model") and record.get("count_model_justified") is not True:
        errors.append("UNJUSTIFIED_COUNT_MODEL")
    return {"level": 8, "engine": "isolated-level8-review-gate-v1",
            "eligible_for_owner_review": not errors,
            "scientific_status": "NOT_VERIFIED", "scientific_score": None,
            "fda_prediction": "ABSTAIN", "errors": sorted(set(errors))}
