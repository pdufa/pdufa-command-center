#!/usr/bin/env python3
"""Fail-closed evidence intake validation for MAIN Phase 3 research records.

Evidence proposals are NOT qualification decisions. No PASS is assigned by this
tool; evidence is merely checked for identity, source and review completeness.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from phase3_qualification_ledger import GATES

NCT = re.compile(r"^NCT\d{8}$")
REQUIRED = {"nct_id", "gate", "source_url", "observed_at_utc", "claim", "reviewer_status"}
REVIEW_STATUSES = {"PENDING", "ACCEPTED", "REJECTED"}

def validate_evidence(ledger, submissions):
    records = ledger.get("records")
    if ledger.get("total") != 741 or not isinstance(records, list) or len(records) != 741:
        raise ValueError("Expected complete 741-record research ledger")
    indexed = {r["nct_id"]: r for r in records}
    if len(indexed) != 741:
        raise ValueError("Duplicate ledger NCT identity")
    if not isinstance(submissions, list):
        raise ValueError("Evidence must be a JSON array")
    results = []
    seen = set()
    for item in submissions:
        if not isinstance(item, dict) or not REQUIRED.issubset(item):
            raise ValueError("Evidence item missing required fields")
        nct, gate = item["nct_id"], item["gate"]
        if not isinstance(nct, str) or not NCT.fullmatch(nct) or nct not in indexed:
            raise ValueError("Unknown NCT identity")
        if gate not in GATES or gate == "registry_identity":
            raise ValueError("Invalid externally reviewed gate")
        key = (nct, gate, item["source_url"])
        if key in seen:
            raise ValueError("Duplicate evidence submission")
        seen.add(key)
        url = item["source_url"]
        if not isinstance(url, str) or not url.startswith("https://") or len(url) < 12:
            raise ValueError("Source must have HTTPS URL")
        if not isinstance(item["claim"], str) or not item["claim"].strip():
            raise ValueError("Nonempty evidence claim required")
        if item["reviewer_status"] not in REVIEW_STATUSES:
            raise ValueError("Invalid reviewer status")
        try:
            observed = datetime.fromisoformat(item["observed_at_utc"].replace("Z", "+00:00"))
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid observed timestamp") from exc
        if observed.tzinfo is None or observed > datetime.now(timezone.utc):
            raise ValueError("Timestamp must be timezone-aware and not future")
        if item["reviewer_status"] == "ACCEPTED" and not (
            isinstance(item.get("reviewer"), str) and item["reviewer"].strip()
            and isinstance(item.get("reviewed_at_utc"), str) and item["reviewed_at_utc"].strip()
        ):
            raise ValueError("Accepted evidence requires reviewer and review timestamp")
        if item["reviewer_status"] == "ACCEPTED":
            try:
                reviewed = datetime.fromisoformat(item["reviewed_at_utc"].replace("Z", "+00:00"))
            except (ValueError, AttributeError) as exc:
                raise ValueError("Invalid reviewer timestamp") from exc
            if reviewed.tzinfo is None or reviewed > datetime.now(timezone.utc):
                raise ValueError("Review timestamp must be timezone-aware and not future")
            if reviewed < observed:
                raise ValueError("Review cannot predate observation")

        results.append({"nct_id": nct, "gate": gate, "source_url": url,
                        "reviewer_status": item["reviewer_status"],
                        "intake_status": "EVIDENCE_RECORDED_NOT_QUALIFIED"})
    return {"report_type": "MAIN_PHASE3_EVIDENCE_INTAKE_RESEARCH_ONLY",
            "ledger_total": 741, "submitted_total": len(results),
            "qualified_pipeline_total": None, "items": results,
            "limitations": "Review status never changes gate scores or promotes Pipeline/GEM."}

def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: phase3_evidence_intake.py <ledger.json> <submissions.json> <output.json>")
    ledger = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    submissions = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result = validate_evidence(ledger, submissions)
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Evidence intake: {result['submitted_total']} submissions; 0 automatic promotions")

if __name__ == "__main__":
    main()
