#!/usr/bin/env python3
"""Read-only, event-level issuer PDUFA provenance audit for the 741-trial research census.

An event is (issuer, asset, application, indication, target), not merely an NCT.
Never treat a company's target announcement as independent FDA documentation.
Do not promote any trial to Pipeline or equate sibling studies to applications.
"""
import json
from datetime import date, datetime, timezone
from pathlib import Path
import sys
from build_phase3_issuer_rights_claim_overlay import build

ROOT = Path(__file__).resolve().parents[1]
CYTK = ROOT / "data/research_issuer_rights_claims_cytk_2026-10-26.json"


def classify_event(event, as_of):
    """A source-dated issuer target is a research lead, not FDA verification."""
    target = date.fromisoformat(event["issuer_reported_target_date"])
    if target <= as_of:
        return "PAST_TARGET_REQUIRES_OUTCOME_RECONCILIATION"
    if event.get("agency_independent_verification") is not False:
        raise ValueError("Unreviewed issuer announcement cannot become FDA-verified")
    if not event.get("issuer_reported_accepted_application"):
        raise ValueError("Issuer target lacks explicit filing-acceptance claim")
    if not event.get("issuer_primary_source_url", "").startswith("https://"):
        raise ValueError("Issuer event missing a primary-source reference")
    return "FUTURE_ISSUER_REPORTED_TARGET_NOT_AGENCY_VERIFIED"


def audit(as_of=None):
    as_of = as_of or date.today()
    base = build()
    if base["denominator_trials"] != 741 or base["denominator_issuers"] != 130:
        raise ValueError("Historical registry denominator changed")
    dossier = json.loads(CYTK.read_text(encoding="utf-8"))
    program = dossier["programs"][0]
    all_issuer_events = base["issuer_reported_future_pdufa_events"]
    issuer_events = [x for x in all_issuer_events if x["ticker"] == "CYTK" and x["asset"] == "aficamten"]
    results = []
    seen = set()
    for event in issuer_events:
        nct = event["nct_id"]
        links = [x for x in program["trialLinks"] if x["nctId"] == nct]
        if len(links) != 1:
            raise ValueError("Event lacks exact NCT in primary issuer program dossier")
        link = links[0]
        if nct in seen:
            raise ValueError("Duplicate NCT application target")
        seen.add(nct)
        if (event["ticker"] != program["issuerTicker"]
                or event["asset"] != program["asset"]
                or event["issuer_reported_target_date"] != link["issuerReportedCurrentPdufaDate"]
                or event["issuer_primary_source_url"] != link["issuerReportedCurrentPdufaSourceUrl"]):
            raise ValueError("Application target does not match issuer dossier")
        status = classify_event(event, as_of)
        results.append({
            "ticker": event["ticker"], "asset": event["asset"],
            "application_type": "sNDA", "supporting_nct": nct,
            "study": link["study"], "indication": event["indication"],
            "issuer_reported_pdufa_target": event["issuer_reported_target_date"],
            "issuer_reported_fda_filing_accepted": True,
            "issuer_source": event["issuer_primary_source_url"],
            "agency_goal_date_document_reviewed": False,
            "fda_independent_goal_date_confirmed": False,
            "application_decision_outcome_verified": False,
            "research_status": status,
            "qualified_pipeline": None,
        })
    return {
        "scope": "CYTK_AFICAMTEN_ONLY_ISSUER_REPORTED_FDA_EVENT_PROVENANCE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluated_as_of": as_of.isoformat(),
        "original_historical_trials": 741,
        "original_issuers": 130,
        "rights_claim_links": base["issuer_rights_claim_evidence_linked_trials"],
        "issuer_reported_events": len(results),
        "scope_excluded_other_issuer_events": len(all_issuer_events) - len(issuer_events),
        "future_issuer_reported_events": sum(x["research_status"].startswith("FUTURE_") for x in results),
        "past_issuer_reported_events_needing_outcome_reconciliation": sum(
            x["research_status"].startswith("PAST_") for x in results),
        "independently_fda_confirmed_events": 0,
        "qualified_pipeline_count": None,
        "events": results,
        "limitations": "No independent FDA goal letter or current decision outcome is attached. Future issuer target is not FDA independently verified. The same drug's other trials and indications do not inherit a PDUFA event. Historical passed dates must be reconciled with an actual decision.",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_issuer_pdufa_event_provenance.py <report.json>")
    report = audit()
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Issuer-reported event candidates:", report["issuer_reported_events"])
    print("Future issuer-reported targets:", report["future_issuer_reported_events"])
    print("Past targets needing outcome reconciliation:", report["past_issuer_reported_events_needing_outcome_reconciliation"])
    print("Independent FDA goal-date confirmation:", report["independently_fda_confirmed_events"])
    print("Qualified Pipeline: UNKNOWN")
