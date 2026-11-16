"""Isolated Level 18 scientific challenge / alternative-explanation intake.

Records owner-authored counterarguments; never fabricates owner review or
acceptance, changes prediction scores, or accesses production state.
"""
from __future__ import annotations

from datetime import date
import re
from typing import Any

_NCT = re.compile(r"NCT[0-9]{8}")


def validate_level18_challenge(record: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    required = ("nct_id", "cutoff_on", "evidence_receipts", "challenges")
    missing = sorted(k for k in required if not record.get(k))
    nct = record.get("nct_id")
    if not isinstance(nct, str) or not _NCT.fullmatch(nct):
        errors.append("INVALID_EXACT_NCT")
    try:
        cutoff_text = record["cutoff_on"]
        if not isinstance(cutoff_text, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cutoff_text):
            raise ValueError("invalid date")
        cutoff = date.fromisoformat(cutoff_text)
    except (KeyError, TypeError, ValueError):
        cutoff = None
        errors.append("INVALID_CUTOFF")
    receipts = record.get("evidence_receipts")
    if not isinstance(receipts, list) or not receipts:
        errors.append("NO_EVIDENCE_RECEIPTS")
        receipts = []
    receipt_ids: set[str] = set()
    for i, item in enumerate(receipts):
        if not isinstance(item, dict):
            errors.append(f"INVALID_RECEIPT_{i}")
            continue
        receipt_id = item.get("receipt_id")
        if not isinstance(receipt_id, str) or not receipt_id.strip():
            errors.append(f"MISSING_RECEIPT_ID_{i}")
        elif receipt_id in receipt_ids:
            errors.append("DUPLICATE_RECEIPT_ID")
        else:
            receipt_ids.add(receipt_id)
        if item.get("nct_id") != nct:
            errors.append(f"RECEIPT_TRIAL_MISMATCH_{i}")
        if not isinstance(item.get("source_url"), str) or not item["source_url"].startswith("https://"):
            errors.append(f"INVALID_RECEIPT_SOURCE_{i}")
        try:
            published = date.fromisoformat(item["published_on"])
            retrieved = date.fromisoformat(item["retrieved_on"])
            if published > retrieved or (cutoff and retrieved > cutoff):
                errors.append(f"POST_CUTOFF_RECEIPT_{i}")
        except (KeyError, ValueError, TypeError):
            errors.append(f"INVALID_RECEIPT_DATES_{i}")
    challenges = record.get("challenges")
    if not isinstance(challenges, list) or not challenges:
        errors.append("NO_CHALLENGES")
        challenges = []
    for i, challenge in enumerate(challenges):
        if not isinstance(challenge, dict):
            errors.append(f"INVALID_CHALLENGE_{i}")
            continue
        for field in ("counterargument", "alternative_explanation", "owner_id"):
            if not isinstance(challenge.get(field), str) or not challenge[field].strip():
                errors.append(f"MISSING_{field.upper()}_{i}")
        refs = challenge.get("evidence_receipt_ids")
        if not isinstance(refs, list) or not refs or any(not isinstance(x, str) or x not in receipt_ids for x in refs):
            errors.append(f"UNLINKED_CHALLENGE_EVIDENCE_{i}")
        if challenge.get("owner_acceptance_claimed") is True:
            errors.append(f"UNVERIFIED_OWNER_ACCEPTANCE_{i}")
    return {
        "level": 18, "engine": "isolated-level18-challenge-contract-v1",
        "eligible_for_owner_review": not missing and not errors,
        "scientific_status": "NOT_VERIFIED", "scientific_score": None,
        "fda_prediction": "ABSTAIN", "missing_fields": missing,
        "errors": sorted(set(errors)),
    }
