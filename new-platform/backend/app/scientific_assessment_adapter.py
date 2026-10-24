"""Read-only bridge for scientific evidence keyed by exact trial identity.

Scientific evidence must never be merged by ticker or used to overwrite
PIPELINE, GEM_JR, or GEM qualification scores.
"""
from __future__ import annotations
from typing import Mapping, Any

def scientific_trial_payload(exact_id: str, evidence: Mapping[str, Any] | None = None) -> dict:
    if not isinstance(exact_id, str) or not exact_id.strip():
        raise ValueError("Exact trial identity required")
    from .scientific_assessment import assess
    result = assess(dict(evidence or {}))
    return {
        "exactId": exact_id,
        "assessment": result,
        "sourceStatus": "provided_evidence" if evidence else "not_loaded",
        "independentOfQualificationPresets": True,
    }
