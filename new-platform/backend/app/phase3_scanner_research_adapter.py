"""Scanner-to-research adapter; discovery is always allowed, deep analysis is gated.

This module is a safe integration seam, not a production scanner registration.
Scanner callers must pass separately verified Phase 3 and PDUFA announcements.
"""
from __future__ import annotations
from .phase3_deep_analysis_orchestrator import prepare_deep_analysis

def route_scanned_candidate(candidate: dict, *, as_of: str) -> dict:
    """Return discovery listing for every candidate, research only if eligible.

    Input:
      exact_key: immutable trial/program identity
      list_memberships: Pipeline/GEM JR/GEM/WT labels
      phase3_results: independently verified public results event
      pdufa_assignment: independently verified PDUFA announcement event
      scientific_evidence: field-level dated verified research sources
    """
    if not isinstance(candidate, dict):
        raise ValueError("Candidate must be a mapping")
    key = candidate.get("exact_key")
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Exact candidate identity required")
    lists = candidate.get("list_memberships", [])
    if not isinstance(lists, list) or any(not isinstance(x, str) for x in lists):
        raise ValueError("List memberships must be a list of names")
    analysis = prepare_deep_analysis(
        exact_key=key,
        phase3_results=candidate.get("phase3_results") or {},
        pdufa_assignment=candidate.get("pdufa_assignment") or {},
        scientific_evidence=candidate.get("scientific_evidence") or {},
        as_of=as_of,
    )
    return {
        "exactKey": key, "asOf": as_of,
        "discoveryVisible": True,
        "listMemberships": lists[:],
        "deepAnalysisEligible": analysis["gate"]["deepAnalysisEligible"],
        "deepAnalysisStatus": analysis["status"],
        "blockReasons": analysis["gate"]["blockReasons"],
        "analysis": analysis if analysis["gate"]["deepAnalysisEligible"] else None,
        "tradeAuthorized": False,
    }
