#!/usr/bin/env python3
"""Audit an FDA outcome-only CSV without exposing outcomes to blind scoring.

Usage:
 python scripts/audit_historical_universe.py --input data/backtest/fda-official-2026-novel-approvals-50-outcome-only-2026-11-18.csv --target 196
"""
import argparse
import csv
import json
from collections import Counter
from datetime import date
from pathlib import Path

def audit(path, target):
    with Path(path).open(newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    errors=[]
    warnings=[]
    if not rows:
        errors.append("Empty outcome file")
    keys=set()
    dates=[]
    for i,row in enumerate(rows,2):
        drug=(row.get("drug_brand") or row.get("drug") or "").strip()
        action=(row.get("approval_date") or row.get("actual_action_date") or "").strip()
        source=(row.get("source_url") or "").strip()
        application=(row.get("application_number") or "").strip()
        if not drug:
            errors.append(f"line {i}: missing drug")
        if not action:
            errors.append(f"line {i}: missing action date")
        else:
            try:
                dates.append(date.fromisoformat(action))
            except ValueError:
                errors.append(f"line {i}: invalid action date")
        if not source.startswith("https://"):
            errors.append(f"line {i}: missing HTTPS source")
        if not application:
            warnings.append(f"line {i}: application number not verified")
        key=(application,action) if application else (drug.lower(),action)
        if key in keys:
            errors.append(f"line {i}: duplicate action key {key}")
        keys.add(key)
        if (row.get("blind_input_allowed") or "").upper() == "YES":
            errors.append(f"line {i}: outcome-only record incorrectly permitted as blind input")
    summary={"source_rows":len(rows),"requested_cases":target,
             "unreconciled_count":max(target-len(rows),0),
             "case_count_verified":False,
             "outcomes_quarantined":True,
             "errors":errors,"warnings":warnings,
             "dates_min":str(min(dates)) if dates else None,
             "dates_max":str(max(dates)) if dates else None}
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--target",type=int,default=196)
    p.add_argument("--output")
    args=p.parse_args()
    result=audit(args.input,args.target)
    payload=json.dumps(result,indent=2)
    if args.output:
        Path(args.output).write_text(payload+"\n",encoding="utf-8")
    print(payload)
    raise SystemExit(1 if result["errors"] else 0)
