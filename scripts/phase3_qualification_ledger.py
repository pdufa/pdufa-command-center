#!/usr/bin/env python3
"""Read-only, fail-closed qualification ledger for the 741-row MAIN research census.

Source identity is NOT evidence of current commercial rights, public listing,
market cap, active development, FDA PDUFA or approval probability.
"""
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
GATES = (
    "registry_identity", "ticker_drug_indication_identity",
    "current_commercial_rights", "active_phase3_development",
    "public_listing", "market_cap_300m_10b", "us_fda_pathway",
    "verified_pdufa", "original_source_freshness",
)
UNKNOWN = "REVIEW"
VALID = {"PASS", "FAIL", "REVIEW"}

def build_ledger(source_report):
    with CENSUS.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 741 or len({r["nct_id"] for r in rows}) != 741:
        raise ValueError("741-row census identity/size mismatch")
    if source_report.get("census_total") != 741:
        raise ValueError("Original registry report has wrong denominator")
    verified = source_report.get("original_source_records")
    if not isinstance(verified, list):
        raise ValueError("Original source records missing")
    indexed = {}
    for record in verified:
        nct = record.get("nct_id")
        if nct in indexed or not nct:
            raise ValueError("Duplicate or missing source identity")
        indexed[nct] = record
    ledger = []
    for row in rows:
        nct = row["nct_id"]
        record = indexed.get(nct)
        matched = bool(
            record and record.get("census_ticker") == row["ticker"]
            and record.get("census_company") == row["company"]
            and record.get("source_sha256")
            and record.get("source") == "https://clinicaltrials.gov/api/v2/studies/" + nct
        )
        gates = {gate: UNKNOWN for gate in GATES}
        if matched:
            gates["registry_identity"] = "PASS"
        if record and record.get("phase3_in_current_registry") is False:
            gates["active_phase3_development"] = "FAIL"
        if record and record.get("status_matches_dated_census") is False:
            # Dated census changes require a new development assessment.
            gates["active_phase3_development"] = "REVIEW"
        ledger.append({
            "nct_id": nct, "ticker": row["ticker"], "company": row["company"],
            "source_url": row["source_url"],
            "source_fetched_at_utc": record.get("fetched_at_utc") if record else None,
            "source_sha256": record.get("source_sha256") if record else None,
            "gates": gates,
            "qualified_pipeline": False if "FAIL" in gates.values() else None,
            "qualification_status": "FAIL" if "FAIL" in gates.values() else "REVIEW",
            "reason": "Registry identity alone does not establish mandatory qualification gates."
        })
    counts = {gate: dict(Counter(row["gates"][gate] for row in ledger)) for gate in GATES}
    return {
        "report_type": "MAIN_PHASE3_QUALIFICATION_EVIDENCE_LEDGER_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "total": 741, "source_verified": counts["registry_identity"].get("PASS", 0),
        "qualified_pipeline_total": None,
        "gate_counts": counts, "records": ledger,
        "limitations": "No automatic production promotion, GEM changes or approval probabilities."
    }

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: phase3_qualification_ledger.py <full-registry-report.json> <output.json>")
    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = build_ledger(report)
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Ledger: {result['source_verified']}/{result['total']} registry identities; qualified Pipeline UNKNOWN")

if __name__ == "__main__":
    main()
