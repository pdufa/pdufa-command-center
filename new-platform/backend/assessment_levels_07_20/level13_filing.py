"""Isolated Level 13 application filing-readiness evidence contract.

This is an evidence inventory, not an FDA application acceptance determination.
It never touches the active assessment runtime or Levels 1–6.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}", re.ASCII)
_APPLICATION = re.compile(r"(?:NDA|BLA)[0-9]{6}", re.ASCII)


def validate_level13_filing(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "application_id", "indication", "review_cycle_id",
                "filing_source_url", "published_on", "retrieved_on", "cutoff_on")
    missing = sorted(k for k in required if not record.get(k))
    nct = record.get("nct_id")
    app = record.get("application_id")
    if not isinstance(nct, str) or _NCT.fullmatch(nct) is None:
        errors.append("INVALID_EXACT_NCT")
    if not isinstance(app, str) or _APPLICATION.fullmatch(app) is None:
        errors.append("INVALID_APPLICATION_ID")
    if not isinstance(record.get("review_cycle_id"), str) or not record.get("review_cycle_id", "").strip():
        errors.append("MISSING_REVIEW_CYCLE_ID")
    if not isinstance(record.get("filing_source_url"), str) or not record["filing_source_url"].startswith("https://"):
        errors.append("INVALID_FILING_SOURCE")
    for field in ("indication",):
        if not isinstance(record.get(field), str) or not record[field].strip():
            errors.append("INVALID_" + field.upper())
    dates: dict[str, date] = {}
    for field in ("published_on", "retrieved_on", "cutoff_on"):
        v = record.get(field)
        try:
            if not isinstance(v, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", v) is None:
                raise ValueError("invalid ISO date")
            dates[field] = date.fromisoformat(v)
        except (TypeError, ValueError):
            errors.append("INVALID_" + field.upper())
    if len(dates) == 3 and not (dates["published_on"] <= dates["retrieved_on"] <= dates["cutoff_on"]):
        errors.append("SOURCE_AFTER_CUTOFF_OR_RETRIEVAL")
    # Exact application-cycle association must be attested by documentary linkage,
    # never inferred from company, ticker, date proximity or trial alone.
    if record.get("exact_linkage_documented") is not True:
        errors.append("EXACT_APPLICATION_CYCLE_LINKAGE_UNDOCUMENTED")
    return {
        "level": 13, "engine": "isolated-level13-filing-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
