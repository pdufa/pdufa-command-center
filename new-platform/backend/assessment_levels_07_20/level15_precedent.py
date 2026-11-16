"""Level 15 FDA precedent/advisory evidence intake, isolated and disabled.

Comparable precedents are context, not approval probabilities. Target outcomes
cannot enter prospective evidence inventories.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

NCT = re.compile(r"NCT[0-9]{8}")


def validate_level15_precedent(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "indication", "treatment_setting", "cutoff_on", "precedents")
    missing = sorted(k for k in required if not record.get(k))
    if not isinstance(record.get("nct_id"), str) or not NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    try:
        cutoff = date.fromisoformat(record["cutoff_on"])
        if not isinstance(record["cutoff_on"], str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", record["cutoff_on"]):
            raise ValueError("invalid")
    except (KeyError, ValueError, TypeError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    precedents = record.get("precedents")
    if not isinstance(precedents, list) or not precedents:
        errors.append("PRECEDENTS_NOT_DOCUMENTED")
        precedents = []
    for i, item in enumerate(precedents):
        if not isinstance(item, dict):
            errors.append(f"INVALID_PRECEDENT_{i}")
            continue
        for key in ("application_id", "indication", "treatment_setting",
                    "official_source_url", "published_on", "retrieved_on",
                    "comparability_rationale"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"MISSING_{key.upper()}_{i}")
        url = item.get("official_source_url")
        if not isinstance(url, str) or not url.startswith("https://"):
            errors.append(f"INVALID_SOURCE_{i}")
        try:
            published = date.fromisoformat(item["published_on"])
            retrieved = date.fromisoformat(item["retrieved_on"])
            if published > retrieved or (cutoff and retrieved > cutoff):
                errors.append(f"POST_CUTOFF_SOURCE_{i}")
        except (KeyError, ValueError, TypeError):
            errors.append(f"INVALID_DATES_{i}")
        if item.get("target_trial_outcome_exposed") is not False:
            errors.append(f"OUTCOME_EXPOSURE_NOT_EXCLUDED_{i}")
        if item.get("is_target_application") is not False:
            errors.append(f"TARGET_APPLICATION_NOT_EXCLUDED_{i}")
    return {
        "level": 15, "engine": "isolated-level15-precedent-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
