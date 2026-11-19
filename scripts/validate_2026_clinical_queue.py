#!/usr/bin/env python3
"""Validate clinical priority queue against its source backlog; never load outcomes."""
import csv
import sys
from pathlib import Path

def load(path):
    with Path(path).open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def validate(source, queue):
    if len(source)!=len(queue):
        raise ValueError(f"Queue/source counts differ: {len(queue)} vs {len(source)}")
    ids=[r["event_id"] for r in source]
    qids=[r["event_id"] for r in queue]
    if len(set(ids))!=len(ids) or len(set(qids))!=len(qids) or set(ids)!=set(qids):
        raise ValueError("Missing or duplicate event IDs")
    expected=[]
    for r in source:
        exposure=r["researcher_outcome_exposure"].upper()
        undated=int(r["undated_leads"] or 0)
        dated=int(r["dated_provisional_claims"] or 0)
        priority=1 if exposure in ("OBSERVED","POTENTIAL") else 2 if undated else 3 if dated else 4
        expected.append((r["event_id"],priority))
    lookup=dict(expected)
    for r in queue:
        if int(r["priority"])!=lookup[r["event_id"]]:
            raise ValueError(f"Incorrect priority for {r['event_id']}")
        if r["blind_lock_ready"]!="NO":
            raise ValueError(f"Premature blind lock readiness for {r['event_id']}")
        if r["evidence_status"]!="INCOMPLETE":
            raise ValueError(f"Unexpected evidence completion status for {r['event_id']}")
    order=[(int(r["priority"]),-int(r["undated_leads"] or 0),r["event_id"]) for r in queue]
    if order!=sorted(order):
        raise ValueError("Queue sort order incorrect")
    return {p:sum(int(r["priority"])==p for r in queue) for p in (1,2,3,4)}

if __name__=="__main__":
    if len(sys.argv)!=3:
        raise SystemExit("usage: validate_2026_clinical_queue.py SOURCE.csv QUEUE.csv")
    print("PASS clinical priority queue",validate(load(sys.argv[1]),load(sys.argv[2])))
