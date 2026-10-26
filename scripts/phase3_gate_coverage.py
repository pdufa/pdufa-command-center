#!/usr/bin/env python3
"""Research-only gate coverage accounting. Evidence intake is not qualification."""
import json
import sys
from pathlib import Path
from phase3_qualification_ledger import GATES

def summarize(ledger, intake):
    records = ledger.get("records")
    if ledger.get("total") != 741 or not isinstance(records, list) or len(records) != 741:
        raise ValueError("Incomplete 741-study ledger")
    indexed = {r["nct_id"]: r for r in records}
    if len(indexed) != 741 or any(set(r.get("gates", {})) != set(GATES) for r in records):
        raise ValueError("Ledger identity or gate mismatch")
    if intake.get("ledger_total") != 741 or intake.get("qualified_pipeline_total") is not None:
        raise ValueError("Intake must be research-only")
    items = intake.get("items")
    if not isinstance(items, list) or intake.get("submitted_total") != len(items):
        raise ValueError("Invalid intake item count")
    statuses = ("PENDING", "ACCEPTED", "REJECTED")
    coverage = {gate: {"records_with_evidence": 0, "evidence_items": 0,
                       "reviewer_status_counts": {s: 0 for s in statuses},
                       "records_without_evidence": 741} for gate in GATES if gate != "registry_identity"}
    distinct = {gate: set() for gate in coverage}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Malformed intake record")
        nct, gate, status = item.get("nct_id"), item.get("gate"), item.get("reviewer_status")
        if nct not in indexed or gate not in coverage or status not in statuses or item.get("intake_status") != "EVIDENCE_RECORDED_NOT_QUALIFIED":
            raise ValueError("Invalid or qualifying intake record")
        coverage[gate]["evidence_items"] += 1
        coverage[gate]["reviewer_status_counts"][status] += 1
        distinct[gate].add(nct)
    for gate, ids in distinct.items():
        coverage[gate]["records_with_evidence"] = len(ids)
        coverage[gate]["records_without_evidence"] = 741 - len(ids)
    return {"report_type": "MAIN_PHASE3_EVIDENCE_COVERAGE_RESEARCH_ONLY",
            "ledger_total": 741, "mandatory_gate_total": len(GATES),
            "externally_reviewed_gate_total": len(coverage),
            "submitted_evidence_total": len(items), "coverage": coverage,
            "qualified_pipeline_total": None,
            "limitations": "Evidence coverage and reviewer labels are not independent source verification or qualification. No Pipeline/GEM promotion."}

def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: phase3_gate_coverage.py <ledger.json> <intake.json> <output.json>")
    result = summarize(json.loads(Path(sys.argv[1]).read_text()),
                       json.loads(Path(sys.argv[2]).read_text()))
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Gate coverage: {result['submitted_evidence_total']} items across {result['externally_reviewed_gate_total']} external gates; qualified Pipeline UNKNOWN")

if __name__ == "__main__":
    main()
