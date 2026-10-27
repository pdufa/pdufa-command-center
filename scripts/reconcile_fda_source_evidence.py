"""Reconcile candidate ledger and FDA source-hash report without promoting records."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def reconcile(ledger, fingerprints):
    by_app = {}
    for record in fingerprints.get("records", []):
        by_app.setdefault(record.get("application_id"), []).append(record)
    entries = []
    for candidate in ledger.get("candidate_review_cycles", []):
        matches = [r for r in by_app.get(candidate.get("application_id"), [])
                   if r.get("official_source_url") == candidate.get("official_source_url")]
        hashed = [r for r in matches if r.get("status") == "BYTES_HASHED_NOT_ADJUDICATED"
                  and isinstance(r.get("sha256"), str) and len(r["sha256"]) == 64]
        hashes = {r["sha256"] for r in hashed}
        if len(hashes) > 1:
            status = "CONFLICTING_SOURCE_HASHES"
        elif len(hashes) == 1:
            status = "SOURCE_HASH_AVAILABLE_ADJUDICATION_PENDING"
        elif matches:
            status = "SOURCE_FETCH_UNSUCCESSFUL_OR_BLOCKED"
        else:
            status = "NO_MATCHING_SOURCE_REPORT"
        entries.append({
            "application_id": candidate.get("application_id"),
            "submission_id": candidate.get("submission_id"),
            "review_cycle": candidate.get("review_cycle"),
            "official_source_url": candidate.get("official_source_url"),
            "status": status,
            "source_sha256": next(iter(hashes)) if len(hashes) == 1 else None,
            "independently_verified": False,
            "model_eligible": False,
        })
    return {"records": entries, "model_eligible": 0, "independently_verified": 0,
            "warning": "Source hashing is not independent FDA outcome verification."}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--fingerprints", type=Path, required=True)
    args = p.parse_args()
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    fingerprints = json.loads(args.fingerprints.read_text(encoding="utf-8"))
    print(json.dumps(reconcile(ledger, fingerprints), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
