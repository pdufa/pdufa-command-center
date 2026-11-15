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
CENSUS = ROOT / "new-platform/frontend/public/phase3-census-2026-10-26.csv"
GATES = (
    "registry_identity", "ticker_drug_indication_identity",
    "current_commercial_rights", "active_phase3_development",
    "public_listing", "market_cap_300m_10b", "us_fda_pathway",
    "verified_pdufa", "original_source_freshness",
)
UNKNOWN = "REVIEW"
VALID = {"PASS", "FAIL", "REVIEW"}

def registry_gate_allows_research(gates, source):
    """Keep a source-confirmed registry change in REVIEW, never promote it.

    Consumers must still verify exact NCT, ticker, source URL and digest binding.
    An unexplained REVIEW does not qualify for this research-only path.
    """
    if not isinstance(gates, dict) or not isinstance(source, dict):
        return False
    state = gates.get("registry_identity")
    if state == "PASS":
        return all(key not in source or source[key] is True for key in
                   ("status_matches_dated_census", "phase3_in_current_registry"))
    matches, phase3 = source.get("status_matches_dated_census"), source.get("phase3_in_current_registry")
    if state != "REVIEW" or type(matches) is not bool or type(phase3) is not bool:
        return False
    if not phase3:
        return True
    before, current = source.get("census_status"), source.get("current_registry_status")
    return (matches is False and isinstance(before, str) and bool(before.strip())
            and isinstance(current, str) and bool(current.strip()) and before != current)


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
    if set(indexed) - {r["nct_id"] for r in rows}:
        raise ValueError("Source report includes NCT IDs outside the dated census")
    ledger = []
    for row in rows:
        nct = row["nct_id"]
        record = indexed.get(nct)
        matched = bool(
            record and record.get("census_ticker") == row["ticker"]
            and record.get("census_company") == row["company"]
            and isinstance(record.get("source_sha256"), str)
            and len(record["source_sha256"]) == 64
            and record.get("phase3_in_current_registry") is True
            and record.get("status_matches_dated_census") is True
            and record.get("source") == "https://clinicaltrials.gov/api/v2/studies/" + nct
        )
        gates = {gate: UNKNOWN for gate in GATES}
        if matched:
            gates["registry_identity"] = "PASS"
        # Registry phase or status changes require independent development review.
        # Historical PHASE3 classification is not proof of an active program.
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
