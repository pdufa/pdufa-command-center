"""Conservative, auditable decision-readiness gate; never issues trade instructions.

Separate from the existing 21 assessment scores and GEM FS/FA presets.
"""
from __future__ import annotations

from math import isfinite


def decision_readiness(*, program_id: str, exact_key: str, assessment_score: float | None,
                       assessment_coverage: float | None, market_review: dict,
                       catalyst_verified: bool, financing_risk_reviewed: bool) -> dict:
    if not program_id.startswith("PDUFA-") or not exact_key.strip():
        raise ValueError("Exact program identity required")
    missing = []
    if (assessment_score is None or isinstance(assessment_score, bool)
            or not isinstance(assessment_score, (int, float))
            or not isfinite(assessment_score) or not 0 <= assessment_score <= 100
            or assessment_coverage is None or isinstance(assessment_coverage, bool)
            or not isinstance(assessment_coverage, (int, float))
            or not isfinite(assessment_coverage) or assessment_coverage < 99.99):
        missing.append("complete verified assessment")
    if (market_review.get("status") != "RESEARCH_ONLY"
            or market_review.get("programId") != program_id
            or market_review.get("exactKey") != exact_key):
        missing.append("exact-program market evidence")
    if catalyst_verified is not True:
        missing.append("verified catalyst")
    if financing_risk_reviewed is not True:
        missing.append("financing and dilution risk review")
    return {"programId": program_id, "exactKey": exact_key,
            "status": "READY_FOR_HUMAN_RESEARCH_REVIEW" if not missing else "NOT_READY",
            "missingRequirements": missing, "tradeCall": None,
            "entryPrice": None, "targetPrice": None, "stopLoss": None,
            "ordersEnabled": False, "assessmentScoreChange": False,
            "fsFaChange": False}
