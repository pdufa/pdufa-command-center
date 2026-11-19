#!/usr/bin/env python3
"""Prioritize clinical evidence backlog without exposing FDA outcomes.
Usage: python scripts/prioritize_2026_clinical_backlog.py --input data/backtest/2026-clinical-evidence-backlog.csv --output data/backtest/2026-clinical-priority-queue.csv
"""
import argparse
import csv
from pathlib import Path

def number(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

def prioritize(rows):
    output=[]
    for row in rows:
        undated=number(row.get("undated_leads"))
        exposed=(row.get("researcher_outcome_exposure") or "").upper() in {"OBSERVED", "POTENTIAL"}
        dated=number(row.get("dated_provisional_claims"))
        if exposed:
            priority=1
            next_action="Verify exposure and assign outcome-unexposed reviewer; quarantine contaminated evidence"
        elif undated:
            priority=2
            next_action="Find contemporaneous dated archived source and verify revision"
        elif dated:
            priority=3
            next_action="Verify publication date, exact application mapping and source content"
        else:
            priority=4
            next_action="Collect dated predecision clinical and regulatory evidence"
        output.append({**row,"priority":priority,"next_action":next_action,
                       "blind_lock_ready":"NO"})
    output.sort(key=lambda r:(r["priority"],-number(r.get("undated_leads")),r.get("event_id","")))
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    with Path(args.input).open(newline="",encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    if not rows:
        raise SystemExit("Empty clinical backlog")
    queue=prioritize(rows)
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(queue[0]),quoting=csv.QUOTE_ALL,lineterminator='\n')
        f.write(','.join(queue[0].keys()) + '\n')
        w.writerows(queue)
    print(f"Prioritized {len(queue)} case records; none certified blind-lock-ready")

if __name__=="__main__":
    main()
