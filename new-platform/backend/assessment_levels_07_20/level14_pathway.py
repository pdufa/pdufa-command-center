"""Isolated Level 14 FDA pathway/designation evidence contract.

Records documentary assertions only; a pathway designation is not approval.
No runtime wiring, shared state, or external calls.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")
_APP = re.compile(r"(?:NDA|BLA)[0-9]{6}")
_ALLOWED = frozenset({"FAST_TRACK", "BREAKTHROUGH_THERAPY", "PRIORITY_REVIEW",
                      "ACCELERATED_APPROVAL", "ORPHAN_DRUG", "RMAT"})


def validate_level14_pathway(record: dict[str, Any]) -> dict[str, Any]:
    required = ("nct_id", "application_id", "indication", "review_cycle_id",
                "pathway", "official_source_url", "published_on", "retrieved_on", "cutoff_on")
    missing = sorted(k for k in required if not record.get(k))
    errors: list[str] = []
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    if not isinstance(record.get("application_id"), str) or not _APP.fullmatch(record["application_id"]):
        errors.append("INVALID_APPLICATION_ID")
    if record.get("pathway") not in _ALLOWED:
        errors.append("INVALID_PATHWAY")
    for key in ("indication", "review_cycle_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            errors.append("INVALID_" + key.upper())
    url = record.get("official_source_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append("INVALID_OFFICIAL_SOURCE")
    if record.get("exact_indication_application_link_documented") is not True:
        errors.append("EXACT_LINKAGE_UNDOCUMENTED")
    dates: dict[str, date] = {}
    for key in ("published_on", "retrieved_on", "cutoff_on"):
        value = record.get(key)
        try:
            if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
                raise ValueError("invalid date")
            dates[key] = date.fromisoformat(value)
        except (ValueError, TypeError):
            errors.append("INVALID_" + key.upper())
    if len(dates) == 3 and not (dates["published_on"] <= dates["retrieved_on"] <= dates["cutoff_on"]):
        errors.append("SOURCE_AFTER_CUTOFF_OR_RETRIEVAL")
    return {
        "level": 14, "engine": "isolated-level14-pathway-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
