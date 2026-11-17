"""Isolated Level 12 independent-study reproducibility evidence inventory.

This validates documented cohort independence; it does not perform a meta-analysis,
infer replication, calculate FDA probabilities, or touch production services.
"""
from __future__ import annotations

from datetime import date
from typing import Any
from .level10_dossier import validate_level10_dossier


def validate_level12_replication(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    dossier = record.get("level10_dossier")
    base = validate_level10_dossier(dossier) if isinstance(dossier, dict) else None
    if base is None or not base["eligible_for_owner_review"]:
        errors.append("LEVEL10_EVIDENCE_NOT_READY")
    if base and base["eligible_for_owner_review"]:
        if record.get("nct_id") != dossier["nct_id"]:
            errors.append("TARGET_TRIAL_MISMATCH")
    studies = record.get("studies")
    if not isinstance(studies, list) or len(studies) < 2:
        errors.append("AT_LEAST_TWO_STUDIES_REQUIRED")
        studies = []
    seen: set[str] = set()
    cohorts: set[str] = set()
    cutoff = record.get("cutoff_on")
    try:
        if not isinstance(cutoff, str) or len(cutoff) != 10:
            raise ValueError("invalid")
        cutoff_date = date.fromisoformat(cutoff)
    except (TypeError, ValueError):
        errors.append("INVALID_CUTOFF")
        cutoff_date = None
    if base and base["eligible_for_owner_review"] and cutoff != dossier["cutoff_on"]:
        errors.append("LEVEL10_CUTOFF_MISMATCH")
    for index, study in enumerate(studies):
        if not isinstance(study, dict):
            errors.append(f"INVALID_STUDY_{index}")
            continue
        identity = study.get("nct_id")
        cohort = study.get("cohort_id")
        if not isinstance(identity, str) or not isinstance(cohort, str) or not cohort.strip():
            errors.append(f"MISSING_STUDY_IDENTITY_{index}")
        else:
            if identity in seen:
                errors.append("DUPLICATE_STUDY")
            seen.add(identity)
            if cohort in cohorts:
                errors.append("POTENTIALLY_OVERLAPPING_COHORT")
            cohorts.add(cohort)
        if study.get("independent_cohort_confirmed") is not True:
            errors.append(f"COHORT_INDEPENDENCE_UNCONFIRMED_{index}")
        if not isinstance(study.get("source_url"), str) or not study["source_url"].startswith("https://"):
            errors.append(f"INVALID_SOURCE_{index}")
        try:
            published = date.fromisoformat(study["published_on"])
            retrieved = date.fromisoformat(study["retrieved_on"])
            if published > retrieved or (cutoff_date and retrieved > cutoff_date):
                errors.append(f"SOURCE_AFTER_CUTOFF_{index}")
        except (KeyError, TypeError, ValueError):
            errors.append(f"INVALID_DATES_{index}")
    return {
        "level": 12, "engine": "isolated-level12-replication-contract-v1",
        "eligible_for_owner_review": not errors,
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None, "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
