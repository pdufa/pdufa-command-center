"""Batch research intake for scanner candidates; read-only and fail-closed.

Discovery rows are retained even when research is blocked. This is an
integration component, not an active scheduled scanner or sheet writer.
"""
from __future__ import annotations
from .phase3_scanner_research_adapter import route_scanned_candidate

MAX_BATCH = 200

def evaluate_candidate_batch(candidates: list, *, as_of: str) -> dict:
    if not isinstance(candidates, list) or len(candidates) > MAX_BATCH:
        raise ValueError("Expected a list of at most 200 candidates")
    results = []
    seen = set()
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise ValueError(f"Candidate {index} is not an object")
        key = candidate.get("exact_key")
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Candidate {index} has no exact identity")
        if key in seen:
            raise ValueError(f"Duplicate exact identity: {key}")
        seen.add(key)
        results.append(route_scanned_candidate(candidate, as_of=as_of))
    eligible = sum(row["deepAnalysisEligible"] for row in results)
    return {
        "asOf": as_of,
        "totalDiscovered": len(results),
        "eligibleForResearch": eligible,
        "blockedFromResearch": len(results)-eligible,
        "rows": results,
        "sheetPopulationStatus": "NOT_WRITTEN",
        "tradeAuthorized": False,
    }
