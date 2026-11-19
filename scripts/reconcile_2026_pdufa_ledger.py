#!/usr/bin/env python3
"""Reconcile source event ledger without exposing FDA outcomes to the blind runner.

Input columns:
source,source_record_id,ticker,drug,indication,decision_date,
application_id,source_url,source_status,source_retrieved_at

Output:
- candidate_events.csv (metadata only; no outcome)
- reconciliation_issues.csv (missing fields, duplicates, unsupported status)

This does NOT claim to retrieve the 183 records. It processes a supplied,
independently snapshotted source ledger and requires human review.
"""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

REQUIRED = ("source", "source_record_id", "ticker", "drug",
            "indication", "decision_date", "application_id",
            "source_url", "source_status", "source_retrieved_at")
OUTCOME_TERMS = ("outcome", "approval", "approved", "rejected", "crl")

def write_csv(path, rows, fields):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def reconcile(source, candidates, issues):
    with open(source, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        missing = [c for c in REQUIRED if c not in headers]
        if missing:
            raise ValueError("Missing required columns: " + ", ".join(missing))
        if any(any(t in h.lower() for t in OUTCOME_TERMS) for h in headers):
            raise ValueError("Outcome-bearing columns must remain in a separate file")
        records = list(reader)

    groups = defaultdict(list)
    flagged = []
    for index, r in enumerate(records, 1):
        missing = [k for k in REQUIRED if not (r.get(k) or "").strip()]
        if missing:
            flagged.append({"row": index, "reason": "missing:" + ",".join(missing),
                            "source_record_id": r.get("source_record_id", "")})
            continue
        key = (r["application_id"].strip().upper(),
               r["indication"].strip().lower(),
               r["decision_date"].strip())
        groups[key].append((index, r))

    output = []
    for key, members in sorted(groups.items()):
        if len(members) != 1:
            for index, r in members:
                flagged.append({"row": index, "reason": "duplicate_application_indication_date",
                                "source_record_id": r["source_record_id"]})
            continue
        index, r = members[0]
        if r["source_status"].strip().lower() not in ("decided", "final"):
            flagged.append({"row": index, "reason": "status_not_final",
                            "source_record_id": r["source_record_id"]})
            continue
        output.append({k: r[k] for k in REQUIRED})

    write_csv(candidates, output, REQUIRED)
    write_csv(issues, flagged, ("row", "reason", "source_record_id"))
    print(f"source_records={len(records)} candidates={len(output)} issues={len(flagged)}")
    print("Candidates require independent event-level verification before scoring.")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--source", required=True)
    p.add_argument("--candidates", required=True)
    p.add_argument("--issues", required=True)
    a = p.parse_args()
    reconcile(a.source, a.candidates, a.issues)
