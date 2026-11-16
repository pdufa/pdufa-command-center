"""Isolated Level 10 disease/standard-of-care dossier contract.

No imports from production services; no database, network, or scheduler writes.
A validated dossier is evidence inventory, NOT a completed scientific review.
"""
from __future__ import annotations

from datetime import date
from typing import Any
import re

NCT = re.compile(r"NCT[0-9]{8}$", re.ASCII)
REQUIRED = ("nct_id", "indication", "disease_subtype", "treatment_setting",
            "source_url", "published_on", "retrieved_on", "cutoff_on",
            "guideline_version", "comparator")


def validate_level10_dossier(record: dict[str, Any]) -> dict[str, Any]:
    """Return a non-predictive, immutable-by-convention validation result."""
    missing = sorted(k for k in REQUIRED if not record.get(k))
    errors: list[str] = []
    nct = record.get("nct_id")
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        errors.append("INVALID_EXACT_NCT")
    url = record.get("source_url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append("SOURCE_MUST_BE_HTTPS")
    dates: dict[str, date] = {}
    for field in ("published_on", "retrieved_on", "cutoff_on"):
        value = record.get(field)
        try:
            if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                raise ValueError("not ISO date")
            dates[field] = date.fromisoformat(value)
        except (ValueError, TypeError):
            errors.append("INVALID_" + field.upper())
    if len(dates) == 3 and not (dates["published_on"] <= dates["retrieved_on"] <= dates["cutoff_on"]):
        errors.append("SOURCE_AFTER_CUTOFF_OR_RETRIEVAL")
    for field in ("indication", "disease_subtype", "treatment_setting",
                  "guideline_version", "comparator"):
        if field in record and (not isinstance(record[field], str) or not record[field].strip()):
            errors.append("INVALID_" + field.upper())
    return {
        "level": 10,
        "engine": "isolated-level10-dossier-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED",
        "fda_prediction": "ABSTAIN",
        "scientific_score": None,
        "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
