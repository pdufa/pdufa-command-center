#!/usr/bin/env python3
"""Create per-trial rights-evidence gaps without inferring rights from lead sponsor.

Original 741 trial records and 130 saved issuer research pointers are immutable.
An exact registry lead sponsor name does NOT prove present ownership or license.
No live requests, approvals, memberships, PDUFA predictions or trades.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
SOURCES = ROOT / "new-platform/frontend/public/phase3-census-sources-2026-10-26.json"
OUTCOMES = ("VERIFIED_RIGHTS", "RIGHTS_NOT_ESTABLISHED")


def build():
    trials = list(csv.DictReader(TRIALS.open(encoding="utf-8-sig", newline="")))
    source = json.loads(SOURCES.read_text(encoding="utf-8"))
    if len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741:
        raise ValueError("Original trial count/identity changed")
    if source.get("scope") != "RESEARCH_POINTERS_ONLY" or source.get("trialCount") != 741 or source.get("companyCount") != 130:
        raise ValueError("Issuer source scope mismatch")
    companies = source["companies"]
    if len(companies) != 130 or len({c["ticker"] for c in companies}) != 130:
        raise ValueError("Original issuer count mismatch")
    by_ticker = {c["ticker"]: c for c in companies}
    rows = []
    for trial in sorted(trials, key=lambda x: x["nct_id"]):
        ticker = trial["ticker"]
        issuer = by_ticker.get(ticker)
        if issuer is None or trial["nct_id"] not in issuer["nctIds"] or trial["company"] not in issuer["leadSponsorNames"]:
            raise ValueError("Exact original sponsor-to-issuer research mapping missing")
        rows.append({
            "nct_id": trial["nct_id"], "ticker": ticker,
            "registry_lead_sponsor_name": trial["company"],
            "registry_record_url": trial["source_url"],
            "issuer_sec_submissions_url": issuer["secSubmissionsUrl"],
            "issuer_homepage_research_pointers": issuer["configuredIssuerHomepages"],
            "issuer_cik": issuer["cik"],
            "registry_sponsor_name_matches_saved_pointer": True,
            "current_development_rights_status": "RIGHTS_NOT_ESTABLISHED",
            "required_evidence": ["CURRENT_LICENSE_OR_OWNERSHIP", "DRUG_AND_INDICATION_LINK",
                                  "RIGHTS_EFFECTIVE_DATE", "PRIMARY_SOURCE_DOCUMENT"],
            "current_rights_primary_source": None,
            "qualified_pipeline": None,
        })
    if len({r["ticker"] for r in rows}) != 130:
        raise ValueError("Original issuer coverage incomplete")
    return {
        "scope": "CURRENT_TRIAL_DEVELOPMENT_RIGHTS_RESEARCH_GAPS_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_trial_csv_sha256": hashlib.sha256(TRIALS.read_bytes()).hexdigest(),
        "trial_count": 741, "issuer_count": 130,
        "exact_saved_sponsor_pointers": len(rows),
        "independently_verified_current_development_rights": 0,
        "rights_not_established": len(rows),
        "qualified_pipeline_count": None,
        "trials": rows,
        "limitations": "No fresh legal evidence fetched. Exact sponsor name, SEC ticker/CIK, or trial listing alone never proves current development rights."
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: build_phase3_rights_evidence_gaps.py <report.json>")
    report = build()
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("Exact registry lead-sponsor pointers:", report["exact_saved_sponsor_pointers"], "/741")
    print("Independently verified current rights:", report["independently_verified_current_development_rights"], "/741")
    print("Rights evidence gaps:", report["rights_not_established"], "/741")
    print("Qualified Pipeline: UNKNOWN.")
