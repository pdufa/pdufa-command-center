"""Isolated Level 16 manufacturing/inspection uncertainty evidence intake.

Public silence is UNKNOWN, not evidence of a deficiency. This contract cannot
claim FDA inspection completion, approval, or nonpublic CMC findings.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_APP = re.compile(r"(?:NDA|BLA)[0-9]{6}")
_STATES = frozenset({"PUBLIC_DOCUMENTED", "UNKNOWN_NONPUBLIC", "NOT_APPLICABLE"})


def validate_level16_manufacturing(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "application_id", "review_cycle_id", "indication",
                "cutoff_on", "cmc_state", "inspection_state")
    missing = sorted(k for k in required if not record.get(k))
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    if not isinstance(record.get("application_id"), str) or not _APP.fullmatch(record["application_id"]):
        errors.append("INVALID_APPLICATION_ID")
    for key in ("review_cycle_id", "indication"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append("INVALID_" + key.upper())
    try:
        cutoff_text = record["cutoff_on"]
        if not isinstance(cutoff_text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cutoff_text):
            raise ValueError("invalid")
        cutoff = date.fromisoformat(cutoff_text)
    except (KeyError, TypeError, ValueError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    if record.get("exact_application_cycle_link_documented") is not True:
        errors.append("EXACT_APPLICATION_CYCLE_LINK_UNDOCUMENTED")
    for subject in ("cmc", "inspection"):
        state = record.get(subject + "_state")
        if state not in _STATES:
            errors.append("INVALID_" + subject.upper() + "_STATE")
        source = record.get(subject + "_source")
        if state == "PUBLIC_DOCUMENTED":
            if not isinstance(source, dict):
                errors.append("MISSING_" + subject.upper() + "_SOURCE")
                continue
            if not isinstance(source.get("official_url"), str) or not source["official_url"].startswith("https://"):
                errors.append("INVALID_" + subject.upper() + "_SOURCE_URL")
            try:
                published = date.fromisoformat(source["published_on"])
                retrieved = date.fromisoformat(source["retrieved_on"])
                if published > retrieved or (cutoff and retrieved > cutoff):
                    errors.append("POST_CUTOFF_" + subject.upper() + "_SOURCE")
            except (KeyError, TypeError, ValueError):
                errors.append("INVALID_" + subject.upper() + "_SOURCE_DATES")
        elif source is not None:
            errors.append("SOURCE_WITHOUT_DOCUMENTED_" + subject.upper() + "_STATE")
    return {
        "level": 16, "engine": "isolated-level16-manufacturing-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
