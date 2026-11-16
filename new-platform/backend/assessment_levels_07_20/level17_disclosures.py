"""Isolated Level 17 sponsor disclosure consistency evidence intake.

Contradictions are recorded, not silently resolved; no live source access or
writes to existing trial histories, scores or production systems.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")


def validate_level17_disclosures(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "cutoff_on", "disclosures")
    missing = sorted(k for k in required if not record.get(k))
    if not isinstance(record.get("nct_id"), str) or not _NCT.fullmatch(record["nct_id"]):
        errors.append("INVALID_EXACT_NCT")
    try:
        cutoff_text = record["cutoff_on"]
        if not isinstance(cutoff_text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cutoff_text):
            raise ValueError("invalid date")
        cutoff = date.fromisoformat(cutoff_text)
    except (KeyError, ValueError, TypeError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    disclosures = record.get("disclosures")
    if not isinstance(disclosures, list) or len(disclosures) < 2:
        errors.append("MULTIPLE_SOURCE_VERSIONS_REQUIRED")
        disclosures = []
    ids: set[str] = set()
    for i, item in enumerate(disclosures):
        if not isinstance(item, dict):
            errors.append(f"INVALID_DISCLOSURE_{i}")
            continue
        if item.get("nct_id") != record.get("nct_id"):
            errors.append(f"DISCLOSURE_TRIAL_MISMATCH_{i}")
        version = item.get("version_id")
        if not isinstance(version, str) or not version.strip():
            errors.append(f"MISSING_VERSION_{i}")
        elif version in ids:
            errors.append("DUPLICATE_VERSION_ID")
        else:
            ids.add(version)
        if not isinstance(item.get("source_url"), str) or not item["source_url"].startswith("https://"):
            errors.append(f"INVALID_SOURCE_{i}")
        if not isinstance(item.get("claim"), str) or not item["claim"].strip():
            errors.append(f"MISSING_CLAIM_{i}")
        try:
            published = date.fromisoformat(item["published_on"])
            retrieved = date.fromisoformat(item["retrieved_on"])
            if published > retrieved or (cutoff and retrieved > cutoff):
                errors.append(f"POST_CUTOFF_DISCLOSURE_{i}")
        except (KeyError, ValueError, TypeError):
            errors.append(f"INVALID_DATES_{i}")
    contradictions = record.get("contradictions", [])
    if not isinstance(contradictions, list):
        errors.append("INVALID_CONTRADICTION_LEDGER")
        contradictions = []
    for i, contradiction in enumerate(contradictions):
        if not isinstance(contradiction, dict):
            errors.append(f"INVALID_CONTRADICTION_{i}")
            continue
        if contradiction.get("first_version") not in ids or contradiction.get("second_version") not in ids:
            errors.append(f"UNLINKED_CONTRADICTION_{i}")
        if not isinstance(contradiction.get("description"), str) or not contradiction["description"].strip():
            errors.append(f"MISSING_CONTRADICTION_RATIONALE_{i}")
    return {
        "level": 17, "engine": "isolated-level17-disclosure-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
        "contradictions_recorded": len(contradictions),
    }
