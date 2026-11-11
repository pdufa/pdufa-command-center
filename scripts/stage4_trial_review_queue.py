#!/usr/bin/env python3
"""Build a deterministic human-review queue from unverified FOCUS retrieval artifacts."""
import json
import sys
from pathlib import Path

def build_queue(roster, registry, triage):
    records = roster.get("records")
    sources = registry.get("trials")
    reviews = triage.get("trials")
    if any(not isinstance(x, list) or len(x) != 29 for x in (records, sources, reviews)):
        raise ValueError("Expected 29 records in each artifact")
    if registry.get("scientific_adjudications") != 0 or triage.get("verified_scientific_adjudications") != 0:
        raise ValueError("Unverified queue cannot include adjudications")
    output = []
    seen = set()
    for row, source, review in zip(records, sources, reviews):
        nct = row.get("nct")
        if not isinstance(nct, str) or nct in seen or source.get("nct") != nct or review.get("nct") != nct:
            raise ValueError("Roster and retrieval identity mismatch")
        seen.add(nct)
        if source.get("prediction") is not None or review.get("prediction") is not None or review.get("verified") is not False:
            raise ValueError("Queue must remain unverified")
        status = source.get("status")
        if status not in ("retrieved", "retrieval_failed"):
            raise ValueError("Invalid retrieval status")
        if status == "retrieval_failed":
            priority, next_action = "retrieval_blocked", "retry_registry_retrieval"
        elif review.get("endpoint_evidence") in ("endpoint_metadata_unavailable", "registered_primary_endpoint_missing"):
            priority, next_action = "source_gap", "locate_and_confirm_registered_primary_endpoint"
        elif review.get("endpoint_evidence") == "posted_primary_outcome_missing":
            priority, next_action = "source_gap", "locate_company_readout_or_publication"
        elif review.get("endpoint_evidence") == "primary_outcome_review_required":
            priority, next_action = "scientific_review", "independently_review_primary_endpoint_statistics_and_safety"
        else:
            raise ValueError("Unknown endpoint evidence status")
        output.append({
            "nct": nct, "ticker": row.get("ticker"),
            "source_url": source.get("source_url") if status == "retrieved" else None,
            "priority": priority, "next_action": next_action,
            "phase_readiness": review.get("readiness"),
            "endpoint_evidence": review.get("endpoint_evidence"),
            "specialist_gates_verified": 0, "adjudication": None, "prediction": None,
        })
    return {"status": "human_review_required", "total": 29,
            "verified_specialist_gates": 0, "verified_adjudications": 0,
            "trials": output}

def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: queue.py roster.json registry.json triage.json")
    payloads = [json.loads(Path(path).read_text(encoding="utf-8")) for path in sys.argv[1:]]
    print(json.dumps(build_queue(*payloads), indent=2))

if __name__ == "__main__":
    main()
