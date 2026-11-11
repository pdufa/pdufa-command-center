#!/usr/bin/env python3
"""Audit a manual FOCUS retrieval artifact; do not claim scientific verification."""
import json
import re
import sys
from pathlib import Path

NCT = re.compile(r"NCT[0-9]{8}\Z")
ENDPOINT_EVIDENCE = {"endpoint_metadata_unavailable", "registered_primary_endpoint_missing",
                     "posted_primary_outcome_missing", "primary_outcome_review_required"}
READINESS = {"retrieval_failed", "phase_unresolved", "phase_appropriate_results_present",
             "phase_appropriate_results_missing", "earlier_phase"}


def audit(registry, triage, roster):
    records = roster.get("records") if isinstance(roster, dict) else None
    if not isinstance(records, list) or len(records) != 29:
        raise ValueError("Invalid canonical FOCUS roster")
    expected = [r.get("nct") for r in records if isinstance(r, dict)]
    if len(expected) != 29 or len(set(expected)) != 29 or any(not isinstance(x, str) or not NCT.fullmatch(x) for x in expected):
        raise ValueError("Invalid roster identifiers")
    if registry.get("scientific_adjudications") != 0 or triage.get("verified_scientific_adjudications") != 0:
        raise ValueError("Unexpected adjudication claim")
    a, b = registry.get("trials"), triage.get("trials")
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != 29 or len(b) != 29:
        raise ValueError("Expected 29 records in each artifact")
    for rows in (a, b):
        if [r.get("nct") for r in rows if isinstance(r, dict)] != expected:
            raise ValueError("Artifact order/identity differs from canonical roster")
    counts = {k: 0 for k in sorted(READINESS)}
    endpoint_counts = {k: 0 for k in sorted(ENDPOINT_EVIDENCE)}
    for source, result in zip(a, b):
        if source.get("status") not in ("retrieved", "retrieval_failed"):
            raise ValueError("Invalid retrieval status")
        if result.get("readiness") not in READINESS:
            raise ValueError("Unknown readiness")
        if result.get("verified") is not False or result.get("prediction") is not None or source.get("prediction") is not None:
            raise ValueError("Unverified artifacts must not contain predictions")
        if source["status"] == "retrieval_failed" and result["readiness"] != "retrieval_failed":
            raise ValueError("Failed retrieval cannot pass triage")
        if source["status"] == "retrieved" and result["readiness"] == "retrieval_failed":
            raise ValueError("Triage inconsistent with retrieval")
        if source["status"] == "retrieved":
            category = result.get("endpoint_evidence")
            if category not in ENDPOINT_EVIDENCE:
                raise ValueError("Missing or unknown endpoint evidence classification")
            endpoint_counts[category] += 1
        counts[result["readiness"]] += 1
    return {"total": 29, "retrieved": sum(r["status"] == "retrieved" for r in a),
            "failed": sum(r["status"] == "retrieval_failed" for r in a),
            "readiness_counts": counts, "endpoint_evidence_counts": endpoint_counts,
            "scientific_verification_complete": False,
            "prediction_count": 0}


def main():
    if len(sys.argv) != 4:
        raise SystemExit("Usage: audit.py registry.json triage.json roster.json")
    inputs = [json.loads(Path(p).read_text(encoding="utf-8")) for p in sys.argv[1:]]
    print(json.dumps(audit(*inputs), indent=2))


if __name__ == "__main__":
    main()
