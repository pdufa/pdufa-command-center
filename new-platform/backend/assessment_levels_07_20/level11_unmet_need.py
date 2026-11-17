"""Level 11 unmet-need evidence inventory, isolated from production.

Requires a source-backed Level 10 dossier receipt; never invents treatment
alternatives, unmet-need conclusions, numerical scores, or FDA probabilities.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from .level10_dossier import validate_level10_dossier


def validate_level11_context(record: dict[str, Any]) -> dict[str, Any]:
    dossier = record.get("level10_dossier")
    base = validate_level10_dossier(dossier) if isinstance(dossier, dict) else None
    errors: list[str] = []
    if base is None or not base["eligible_for_owner_review"]:
        errors.append("LEVEL10_EVIDENCE_NOT_READY")
    required = ("nct_id", "indication", "treatment_setting", "alternatives",
                "burden_source_url", "published_on", "retrieved_on", "cutoff_on")
    missing = sorted(k for k in required if not record.get(k))
    if base is not None:
        for key in ("nct_id", "indication", "treatment_setting"):
            if record.get(key) != dossier.get(key):
                errors.append("LEVEL10_IDENTITY_MISMATCH_" + key.upper())
    alternatives = record.get("alternatives")
    if alternatives is not None and (not isinstance(alternatives, list)
                                     or not alternatives
                                     or any(not isinstance(v, str) or not v.strip() for v in alternatives)):
        errors.append("INVALID_ALTERNATIVES")
    url = record.get("burden_source_url")
    if url is not None and (not isinstance(url, str) or not url.startswith("https://")):
        errors.append("INVALID_BURDEN_SOURCE_URL")
    parsed = {}
    for field in ("published_on", "retrieved_on", "cutoff_on"):
        v = record.get(field)
        try:
            if not isinstance(v, str) or len(v) != 10 or v[4] != "-" or v[7] != "-":
                raise ValueError("invalid date")
            parsed[field] = date.fromisoformat(v)
        except (ValueError, TypeError):
            errors.append("INVALID_" + field.upper())
    if len(parsed) == 3 and not (parsed["published_on"] <= parsed["retrieved_on"] <= parsed["cutoff_on"]):
        errors.append("SOURCE_AFTER_CUTOFF_OR_RETRIEVAL")
    if base is not None and base["eligible_for_owner_review"] and "cutoff_on" in parsed:
        if date.fromisoformat(dossier["cutoff_on"]) != parsed["cutoff_on"]:
            errors.append("LEVEL10_CUTOFF_MISMATCH")
    return {
        "level": 11,
        "engine": "isolated-level11-unmet-need-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
