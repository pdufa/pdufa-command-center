"""Additive market-evidence review for existing Pipeline/GEM JR/GEM assessments.

Never modifies scores, qualification, presets, or source evidence.
"""
from __future__ import annotations

from math import isfinite


def market_evidence_review(program_id: str, exact_key: str, signals: dict) -> dict:
    if not isinstance(program_id, str) or not program_id.startswith("PDUFA-"):
        raise ValueError("Immutable program identity required")
    if not isinstance(exact_key, str) or not exact_key.strip():
        raise ValueError("Exact trial source key required")
    status = signals.get("status")
    momentum = signals.get("return20Pct")
    volume = signals.get("volumeRatio20")
    valid = (status == "OK" and isinstance(momentum, (int, float))
             and not isinstance(momentum, bool) and isfinite(momentum)
             and isinstance(volume, (int, float)) and not isinstance(volume, bool)
             and isfinite(volume) and volume >= 0)
    if not valid:
        return {"programId": program_id, "exactKey": exact_key,
                "status": "INSUFFICIENT_EVIDENCE", "observations": [],
                "recommendation": None, "assessmentScoreChange": False,
                "qualificationChange": False, "fsFaChange": False}
    observations = [
        {"metric": "20-bar price change", "value": round(momentum, 4), "unit": "%"},
        {"metric": "Latest IEX volume / 20-bar average", "value": round(volume, 4), "unit": "ratio"},
    ]
    return {"programId": program_id, "exactKey": exact_key,
            "status": "RESEARCH_ONLY", "observations": observations,
            "coverage": "IEX_ONLY_NOT_CONSOLIDATED",
            "recommendation": None, "assessmentScoreChange": False,
            "qualificationChange": False, "fsFaChange": False}
