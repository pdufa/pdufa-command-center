"""Strict adapter from an existing completed assessment to decision-readiness inputs.

Does not recalculate or overwrite the existing 21 assessments.
"""
from __future__ import annotations

from math import isfinite


def assessment_readiness_inputs(record: dict, *, program_id: str, exact_key: str,
                                stage: str = "GEM_JR") -> dict:
    if stage not in {"GEM_JR", "GEM"}:
        raise ValueError("Only GEM JR and GEM assessments are eligible")
    if record.get("programId") != program_id or record.get("exactKey") != exact_key:
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
