#!/usr/bin/env python3
"""Research-only sponsor attribution evidence; sponsor is NOT commercial rights."""
import csv
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"

def build(report):
    with CENSUS.open(encoding="utf-8-sig", newline="") as f:
        census = list(csv.DictReader(f))
    if len(census) != 741 or len({r["nct_id"] for r in census}) != 741:
        raise ValueError("Census identity mismatch")
    if report.get("census_total") != 741:
        raise ValueError("Source report denominator mismatch")
    originals = report.get("original_source_records")
    if not isinstance(originals, list):
        raise ValueError("Original source evidence absent")
    by_nct = {}
    for record in originals:
        nct = record.get("nct_id")
        if not nct or nct in by_nct:
            raise ValueError("Duplicate or missing NCT evidence")
        by_nct[nct] = record
    if set(by_nct) - {r["nct_id"] for r in census}:
        raise ValueError("Extraneous NCT evidence")
    rows = []
    for row in census:
        source = by_nct.get(row["nct_id"])
        matched = bool(source and source.get("census_ticker") == row["ticker"]
                       and source.get("census_company") == row["company"]
                       and source.get("source") == "https://clinicaltrials.gov/api/v2/studies/" + row["nct_id"]
                       and isinstance(source.get("source_sha256"), str)
                       and len(source["source_sha256"]) == 64)
        sponsor = source.get("currently_registered_lead_sponsor") if matched else None
        sponsor = sponsor.strip() if isinstance(sponsor, str) else None
        sponsor = sponsor or None
        rows.append({
            "nct_id": row["nct_id"], "census_ticker": row["ticker"],
            "census_company": row["company"], "registry_lead_sponsor": sponsor,
            "registry_identity": "PASS" if matched else "REVIEW",
            "sponsor_name_present": bool(sponsor),
            "sponsor_matches_census_company": None,
            "current_commercial_rights": "REVIEW",
            "source_url": source.get("source") if matched else None,
            "source_sha256": source.get("source_sha256") if matched else None,
            "note": "Registered lead sponsor is a research lead, not proof of ownership, licensing, or current commercial rights."
        })
    counts = Counter("PRESENT" if r["sponsor_name_present"] else "MISSING" for r in rows)
    return {"report_type": "MAIN_PHASE3_SPONSOR_ATTRIBUTION_RESEARCH_ONLY",
            "total": 741, "source_identity_pass": sum(r["registry_identity"] == "PASS" for r in rows),
            "sponsor_present": counts["PRESENT"], "sponsor_missing": counts["MISSING"],
            "commercial_rights_verified": 0,
            "commercial_rights_verified_denominator": 741,
            "qualified_pipeline_total": None, "records": rows,
            "limitations": "No name-based rights inference; no automatic Pipeline or GEM changes."}

def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: phase3_sponsor_evidence.py <original-registry-report.json> <output.json>")
    result = build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))
    path = Path(sys.argv[2])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Sponsor attribution: {result['sponsor_present']}/741 present; rights unverified 741/741")

if __name__ == "__main__":
    main()
