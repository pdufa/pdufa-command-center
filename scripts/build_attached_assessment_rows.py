#!/usr/bin/env python3
"""Build one main row plus one L01 child row per sourced FDA event.

This tool NEVER invents event records or assessment results.
It refuses to pad an incomplete source ledger to the target count.
"""
import argparse
import csv
from pathlib import Path

FIELDS = ["row_type","parent_event_id","event_id","ticker","drug","indication",
          "decision_date","level","prediction","score","confidence",
          "evidence_cutoff","evidence_status","actual_fda_outcome",
          "prediction_correct","verification_status","source_url"]

def build(source, output, expected=183):
    with open(source, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        required = {"event_id","ticker","drug","indication","decision_date","source_url"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Missing columns: " + ", ".join(sorted(required-set(reader.fieldnames or []))))
        if any("outcome" in name.lower() or "approved" in name.lower()
               for name in (reader.fieldnames or [])):
            raise ValueError("Outcome-bearing input is not permitted in blind layout")
        records = list(reader)
    ids = [r["event_id"].strip() for r in records]
    if any(not identifier for identifier in ids) or len(ids) != len(set(ids)):
        raise ValueError("Blank or duplicate event IDs")
    if len(records) != expected:
        raise ValueError(f"Expected {expected} sourced events, found {len(records)}. No placeholder events generated.")
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for r in records:
            common = {k:r.get(k,"") for k in ("event_id","ticker","drug","indication","decision_date","source_url")}
            writer.writerow({**common,"row_type":"MAIN","parent_event_id":r["event_id"],
                             "verification_status":"PENDING"})
            for n in (1,):
                writer.writerow({**common,"row_type":"ASSESSMENT",
                                 "parent_event_id":r["event_id"],"level":f"L{n:02d}",
                                 "evidence_status":"NOT_COLLECTED",
                                 "verification_status":"PENDING"})
    print(f"Wrote {expected} main rows and {expected} L01 assessment rows to {output}")

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",required=True)
    parser.add_argument("--output",required=True)
    parser.add_argument("--expected",type=int,default=183)
    a=parser.parse_args()
    build(a.source,a.output,a.expected)
