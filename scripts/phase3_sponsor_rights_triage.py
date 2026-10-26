#!/usr/bin/env python3
"""Produce source-linked sponsor/rights review queue; sponsor name is not proof of rights."""
import json
import sys
from pathlib import Path

def build_queue(ledger, registry):
    records = ledger.get("records")
    sources = registry.get("original_source_records")
    if ledger.get("total") != 741 or not isinstance(records, list) or len(records) != 741:
        raise ValueError("Complete ledger required")
    if registry.get("census_total") != 741 or not isinstance(sources, list) or len(sources) != 741 or registry.get("source_errors"):
        raise ValueError("Complete error-free registry evidence required")
    indexed = {r["nct_id"]: r for r in sources}
    if len(indexed) != 741 or len({r["nct_id"] for r in records}) != 741 or set(indexed) != {r["nct_id"] for r in records}:
        raise ValueError("Source and ledger identities must match exactly")
    items = []
    for row in records:
        nct = row["nct_id"]
        source = indexed[nct]
        if row["gates"].get("registry_identity") != "PASS" or row["gates"].get("current_commercial_rights") != "REVIEW":
            raise ValueError("Research queue cannot override qualification gates")
        if source.get("census_ticker") != row["ticker"] or source.get("census_company") != row["company"]:
            raise ValueError("Ticker/company source mismatch")
        if source.get("source") != f"https://clinicaltrials.gov/api/v2/studies/{nct}":
            raise ValueError("Original registry URL mismatch")
        name = source.get("currently_registered_lead_sponsor")
        if name is not None and (not isinstance(name, str) or not name.strip()):
            raise ValueError("Invalid sponsor name")
        items.append({"nct_id": nct, "ticker": row["ticker"], "census_company": row["company"],
                      "registered_lead_sponsor": name, "original_registry_url": source["source"],
                      "source_sha256": source.get("source_sha256"),
                      "source_fetched_at_utc": source.get("fetched_at_utc"),
                      "review_gate": "current_commercial_rights", "review_status": "REVIEW",
                      "commercial_rights_verified": False,
                      "required_next_evidence": "Current company filings or licensing disclosures independently establishing commercial development rights."})
    return {"report_type": "MAIN_PHASE3_SPONSOR_RIGHTS_REVIEW_QUEUE_RESEARCH_ONLY",
            "total": 741, "review_required": len(items), "qualified_pipeline_total": None,
            "items": items,
            "limitations": "ClinicalTrials.gov lead sponsor is not proof of ownership, public listing, commercial rights, active development or FDA PDUFA."}

def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: phase3_sponsor_rights_triage.py <ledger.json> <registry.json> <output.json>")
    result = build_queue(json.loads(Path(sys.argv[1]).read_text()),
                         json.loads(Path(sys.argv[2]).read_text()))
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Sponsor/rights review queue: {result['review_required']}/{result['total']} require independent rights evidence")

if __name__ == "__main__":
    main()
