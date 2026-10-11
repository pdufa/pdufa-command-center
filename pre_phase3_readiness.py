"""Transparent PRE PHASE 3 tab readiness; separate from post-P3 ENTRY READY.

This assesses saved research-source coverage and clinical-assessment validation.
It never produces a trading recommendation or FDA approval probability.
"""
from __future__ import annotations

from numbers import Number

SOURCES = (
    "Clinical trial pipeline",
    "Phase 3 result intake",
    "Phase 3 primary statistics",
    "Phase 2 primary p intake",
    "Pre-readout protocol",
    "Market capitalization",
)


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1


def check_pre_phase3_readiness(manifest, trials, protocol_state=None, phase2_state=None):
    """Return an auditable status from source health and scored research pilots.

    Source-ingestion completion is distinct from human-validated clinical
    scoring and end-to-end browser UI acceptance. An uncalibrated 100-point
    research rubric is not Phase 3 success probability.
    """
    health = {row.get("Source"): row for row in (manifest or {}).get("source_checks", [])
              if isinstance(row, dict)}
    trials = trials or []
    protocol_state = protocol_state or {}
    phase2_state = phase2_state or {}
    checks = []

    def record(name, passed, evidence):
        checks.append({"Requirement": name, "Status": "PASS" if passed else "BLOCKED",
                       "Evidence / next action": str(evidence)})

    clinical = [r for r in trials if r.get("Trial phase") in ("Phase 3", "Phase 2/3")]
    record("Clinical research trial universe", bool(clinical),
           f"{len(clinical)} Phase 3 or Phase 2/3 rows; registry data is not an issuer readout")
    for source in SOURCES:
        row = health.get(source) or {}
        state = row.get("Health") or "MISSING"
        record(source + " feed", state == "RECENT",
               f"{state}; last checked {row.get('Last checked UTC') or 'unknown'}")

    total = _int(protocol_state.get("active_registry_unposted_phase3_trials"))
    stored = _int(protocol_state.get("protocol_records_stored"))
    left = _int(protocol_state.get("uncollected_trials"))
    issues = protocol_state.get("errors")
    protocol_ok = (total > 0 and stored >= total and left == 0
                   and protocol_state.get("status") == "COMPLETE" and not issues)
    record("Active Phase 3 protocol coverage", protocol_ok,
           f"{stored}/{total} active studies saved; {left} uncollected; refresh incomplete studies")

    linked = _int(phase2_state.get("linked_unique_phase2_nct"))
    queried = _int(phase2_state.get("phase2_nct_queried_this_run"))
    unattempted = _int(phase2_state.get("unattempted_linked_nct"))
    phase2_ok = (linked >= 0 and queried >= linked and unattempted == 0
                 and phase2_state.get("status") == "COMPLETE"
                 and not phase2_state.get("errors"))
    record("Exact-linked Phase 2 collector coverage", phase2_ok,
           f"{queried}/{linked} linked NCTs queried; {unattempted} unattempted. "
           "No published primary p-value is not a failed trial")

    linked_p = sum(_int(r.get("Phase 2 PRIMARY evidence count")) for r in clinical
                   if _int(r.get("Phase 2 PRIMARY evidence count")) > 0)
    record("Phase 2 p provenance in dashboard", linked_p > 0,
           f"{linked_p} source-dated linked PRIMARY analyses surfaced; "
           "if zero, validate exact-NCT coverage or confirm no eligible results")

    scored = sum(
        isinstance(r.get("Pre-readout research score /100"), Number)
        and not isinstance(r.get("Pre-readout research score /100"), bool)
        and 0 <= r["Pre-readout research score /100"] <= 100
        and r.get("Score status") == "100-POINT RESEARCH SCORE — UNCALIBRATED"
        for r in clinical
    )
    record("Live source-reviewed pre-readout scoring pilot", scored > 0,
           f"{scored} fully sourced, reviewer-scored Phase 3 trial(s); "
           "complete exact-NCT evidence and issuer readout check for a pilot")

    pending = [c for c in checks if c["Status"] != "PASS"]
    return {
        "status": "BLOCKED — NOT COMPLETE" if pending else "READY FOR FINAL BROWSER ACCEPTANCE",
        "checks": checks,
        "passed": len(checks)-len(pending), "total": len(checks),
        "blocked": [c["Requirement"] for c in pending],
        "phase3_rows": len(clinical), "phase2_p_analyses_visible": linked_p,
        "live_scored_pilots": scored,
        "note": "This is PRE PHASE 3 research-tab readiness only; no trading ENTRY READY or calibrated success probability.",
    }
