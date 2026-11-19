#!/usr/bin/env python3
"""Generate source-review packets from provisional leads without outcome exposure."""
import csv
import json
from collections import defaultdict
from pathlib import Path
from datetime import date

ROOT=Path(__file__).resolve().parents[1]
INPUT=ROOT/"data/backtest/2026-provisional-source-research.csv"
BACKLOG=ROOT/"data/backtest/2026-clinical-evidence-backlog.csv"
OUTPUT=ROOT/"data/backtest/2026-blind-source-review-packets.json"

def read(path):
    with path.open(newline="",encoding="utf-8") as f:
        return list(csv.DictReader(f))

def build():
    cases={r["event_id"]:r for r in read(BACKLOG)}
    leads=defaultdict(list)
    for row in read(INPUT):
        event=row["event_id"]
        if event not in cases:
            raise ValueError("Source lead references unknown event: "+event)
        cutoff=date.fromisoformat(row["cutoff_date"])
        dates=[]
        for key in ("first_public_date","cited_version_public_date"):
            value=row[key]
            if value:
                dates.append(date.fromisoformat(value))
        chronology=("PROVISIONAL_PRE_CUTOFF" if len(dates)==2 and all(d<=cutoff for d in dates)
                    else "MISSING_PUBLICATION_DATE" if len(dates)!=2 else "POST_CUTOFF_INELIGIBLE")
        leads[event].append({
            "source_url":row["source_url"],
            "source_kind":row["source_kind"],
            "source_title":row["source_title"],
            "nct_candidates":row["trial_ids"].split("|") if row["trial_ids"] else [],
            "domain":row["evidence_domain"],
            "first_public_date":row["first_public_date"],
            "cited_version_public_date":row["cited_version_public_date"],
            "cutoff_date":row["cutoff_date"],
            "chronology_screen":chronology,
            "original_version_verified":False,
            "trial_application_linkage_verified":False,
            "scientific_criterion_reviewed":False
        })
    return {
        "kind":"PROVISIONAL_BLIND_SOURCE_REVIEW_PACKETS",
        "disclaimer":"Research leads only. Not source-authenticated, not locked predictions, not FDA outcomes.",
        "cases":[{
            "event_id":event,
            "researcher_outcome_exposure":case["researcher_outcome_exposure"],
            "blind_review_eligible":False,
            "blind_prediction":"NOT_ISSUED",
            "sources":leads[event]
        } for event,case in sorted(cases.items())]
    }

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    content=json.dumps(build(),indent=2,ensure_ascii=False)+"\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8")!=content:
            raise SystemExit("Review packets stale; regenerate without --check")
    else:
        OUTPUT.write_text(content,encoding="utf-8")
    print("Validated provisional source review packets")
