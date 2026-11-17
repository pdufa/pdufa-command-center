"""Isolated Level 7 reviewed subgroup-evidence readiness gate.

A method's calculated interval is not scientific verification. This contract
does not call or modify the existing Level 7 production engine.
"""
from __future__ import annotations
from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_CRITERIA = ("population_definition", "eligibility_applicability", "baseline_balance",
             "subgroup_prespecification", "multiplicity_adjudication",
             "interaction_interpretation", "clinical_generalizability")


def validate_level7_review(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_NCT")
    if not isinstance(record.get("population"), str) or not record["population"].strip():
        errors.append("MISSING_POPULATION")
    try:
        cutoff = date.fromisoformat(record["cutoff_on"])
    except (KeyError, TypeError, ValueError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    for name in _CRITERIA:
        review = record.get(name)
        if not isinstance(review, dict) or review.get("status") != "REVIEWED":
            errors.append("UNREVIEWED_" + name.upper())
            continue
        if review.get("nct_id") != record.get("nct_id"):
            errors.append("WRONG_TRIAL_" + name.upper())
        if not isinstance(review.get("source_url"), str) or not review["source_url"].startswith("https://"):
            errors.append("MISSING_SOURCE_" + name.upper())
        if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
            errors.append("MISSING_RATIONALE_" + name.upper())
        try:
            if cutoff and date.fromisoformat(review["reviewed_on"]) > cutoff:
                errors.append("POST_CUTOFF_" + name.upper())
        except (KeyError, TypeError, ValueError):
            errors.append("INVALID_REVIEW_DATE_" + name.upper())
    return {"level": 7, "engine": "isolated-level7-review-gate-v1",
            "eligible_for_owner_review": not errors,
            "scientific_status": "NOT_VERIFIED", "scientific_score": None,
            "fda_prediction": "ABSTAIN", "errors": sorted(set(errors))}
