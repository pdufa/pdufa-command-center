"""Strict adapter from an existing completed assessment to decision-readiness inputs.

Does not recalculate or overwrite the existing 21 assessments.
"""
from __future__ import annotations

from math import isfinite


def assessment_readiness_inputs(record: dict, *, program_id: str, exact_key: str,
                                stage: str = "GEM_JR") -> dict:
    if stage not in {"GEM_JR", "GEM"}:
        raise ValueError("Only GEM JR and GEM assessments are eligible")
    candidate = (record.get("data") or {}).get("candidate") or {}
    if (record.get("programId") != program_id or record.get("id") != exact_key
            or candidate.get("id") != exact_key or candidate.get("programId") != program_id):
        return {"assessment_score": None, "assessment_coverage": None,
                "status": "IDENTITY_MISMATCH"}
    model = (record.get("models") or {}).get(stage)
    if not isinstance(model, dict):
        return {"assessment_score": None, "assessment_coverage": None,
                "status": "ASSESSMENT_MISSING"}
    score, coverage = model.get("score"), model.get("coverage")
    valid = all(isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v)
                for v in (score, coverage))
    if not valid or not 0 <= score <= 100 or not 99.99 <= coverage <= 100:
        return {"assessment_score": None, "assessment_coverage": None,
                "status": "ASSESSMENT_INCOMPLETE"}
    return {"assessment_score": float(score), "assessment_coverage": float(coverage),
            "status": "COMPLETE"}


def readiness_from_existing_assessment(*, program_id: str, exact_key: str,
                                       record: dict, market_review: dict,
                                       catalyst_verified: bool = False,
                                       financing_risk_reviewed: bool = False,
                                       stage: str = "GEM_JR") -> dict:
    """Read-only adapter: an assessment alone never authorizes a trade."""
    from .decision_readiness import decision_readiness
    verified = assessment_readiness_inputs(record, program_id=program_id,
                                           exact_key=exact_key, stage=stage)
    result = decision_readiness(
        program_id=program_id, exact_key=exact_key,
        assessment_score=verified["assessment_score"],
        assessment_coverage=verified["assessment_coverage"],
        market_review=market_review,
        catalyst_verified=catalyst_verified,
        financing_risk_reviewed=financing_risk_reviewed,
    )
    return {**result, "assessmentEvidenceStatus": verified["status"], "assessmentStage": stage}
