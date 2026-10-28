"""Strict eligibility gate: never analyze before published Phase 3 results AND known PDUFA date.

A scheduled scan may discover candidates earlier, but deep SCIENCE/OUTCOME/MAIN
must remain blocked. Dates are independently verified against as-of time.
"""
from __future__ import annotations
from datetime import date
from urllib.parse import urlparse

def _verified_event(event: dict, as_of: date, *, require_date: bool = True) -> bool:
    if not isinstance(event, dict) or event.get("review_status") != "VERIFIED":
        return False
    url = event.get("source_url")
    parsed = urlparse(url) if isinstance(url, str) else None
    if not parsed or parsed.scheme != "https" or not parsed.netloc:
        return False
    try:
        published = date.fromisoformat(event["published_at"])
        occurred = date.fromisoformat(event["event_date"]) if require_date else published
    except (KeyError, ValueError, TypeError):
        return False
    return published <= as_of and occurred <= as_of

def phase3_pdufa_eligibility(*, exact_key: str, phase3_results: dict,
                             pdufa_assignment: dict, as_of: str) -> dict:
    """Return a fail-closed gate; never infer publication from trial completion.

    phase3_results.event_date: public Phase 3 results release date.
    pdufa_assignment.event_date: date the PDUFA target was publicly assigned.
    pdufa_assignment.pdufa_target_date: the FDA target date (may be future).
    """
    if not isinstance(exact_key, str) or not exact_key.strip():
        raise ValueError("Exact trial/program identity required")
    cutoff = date.fromisoformat(as_of)
    phase3_ok = _verified_event(phase3_results, cutoff)
    pdufa_ok = _verified_event(pdufa_assignment, cutoff)
    target = None
    if pdufa_ok:
        try:
            target = date.fromisoformat(pdufa_assignment["pdufa_target_date"]).isoformat()
        except (KeyError, ValueError, TypeError):
            pdufa_ok = False
    reasons = []
    if not phase3_ok:
        reasons.append("PHASE3_RESULTS_NOT_VERIFIED_AS_PUBLISHED")
    if not pdufa_ok:
        reasons.append("PDUFA_DATE_NOT_VERIFIED_AS_ANNOUNCED")
    eligible = phase3_ok and pdufa_ok
    return {
        "exactKey": exact_key, "asOf": as_of,
        "phase3ResultsVerified": phase3_ok, "pdufaDateVerified": pdufa_ok,
        "pdufaTargetDate": target if pdufa_ok else None,
        "deepAnalysisEligible": eligible,
        "scienceStatus": "ELIGIBLE_TO_START" if eligible else "BLOCKED",
        "outcomeStatus": "ELIGIBLE_TO_START" if eligible else "BLOCKED",
        "mainStatus": "ELIGIBLE_TO_START" if eligible else "BLOCKED",
        "blockReasons": reasons, "approvalProbability": None,
        "tradeAuthorized": False,
    }
