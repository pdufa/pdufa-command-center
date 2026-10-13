#!/usr/bin/env python3
"""Publish a fail-closed GEM ranking-calibration report and source-research queue.

Reads only externally documented, dated historical snapshots and verified OHLCV.
Current FDA approval labels are never converted into historical investment returns.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from gem_calibration import SNAPSHOT_FIELDS, calibrate  # noqa:E402
from post_phase3_trade_backtest import BAR_FIELDS, read_csv  # noqa:E402
from post_phase3_backfill_queue import build_backfill_queue  # noqa:E402

QUEUE_COLUMNS=(
    "research_source","event_key_reference","ticker","pdufa_date_reference",
    "priority","outstanding_requirements","historical_GEM_trade_qualified",
)


def validated_csv(path, required):
    file=Path(path)
    if not file.is_file():
        raise ValueError("Missing input file: "+str(file))
    with file.open(newline="",encoding="utf-8-sig") as f:
        first=next(csv.reader(f),[])
    if len(first)!=len(set(first)) or not set(required).issubset(first):
        raise ValueError("Missing or duplicate fields in "+str(file))
    return read_csv(file)


def source_research_queue(root):
    existing, meta=build_backfill_queue(root)
    researched=[]
    seen=set()
    for r in existing:
        key=str(r.get("event_key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        researched.append({
            "research_source":"CURRENT_SAVED_REGULATORY_PIPELINE_REFERENCE",
            "event_key_reference":key,
            "ticker":r.get("ticker",""),
            "pdufa_date_reference":r.get("pdufa_date_reference",""),
            "priority":r.get("priority",""),
            "outstanding_requirements":r.get("missing_historical_requirements",""),
            "historical_GEM_trade_qualified":"NO — RESEARCH ONLY",
        })
    legacy=read_csv(Path(root)/"historical_assessed_decisions.csv")
    for r in legacy:
        key=str(r.get("event_key") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        researched.append({
            "research_source":"HISTORICAL_FDA_DECISION_RESEARCH_REFERENCE",
            "event_key_reference":key,
            "ticker":r.get("ticker",""),
            "pdufa_date_reference":r.get("pdufa_date",""),
            "priority":"4 — VERIFY WHOLE PROGRAM BEFORE STOCK STUDY",
            "outstanding_requirements":(
                "Historical NCT/exact issuer linkage; source-dated primary endpoint; "
                "first/second financing event filings and FIRST public disclosure dates; "
                "point-in-time score snapshots and OHLCV with split adjustment; "
                "early FDA action and delisted survivor coverage"
            ),
            "historical_GEM_trade_qualified":"NO — RESEARCH ONLY",
        })
    researched.sort(key=lambda r:(r["priority"],r["ticker"],r["event_key_reference"]))
    return researched, {
        "current_pipeline_research_records":len(existing),
        "historical_fda_decision_research_records":len(legacy),
        "unique_nonpromoted_research_items":len(researched),
        "warnings":(
            "FDA outcomes and retrospective financing sources are only leads. "
            "They cannot be assigned historical GEM scores or stock returns."
        ),
        "prior_research_summary":meta,
    }


def write_rows(path,columns,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--report",type=Path,default=ROOT/"data/gem_validation_report.json")
    parser.add_argument("--queue-output",type=Path,default=ROOT/"data/gem_historical_research_queue.csv")
    parser.add_argument("--as-of",type=str)
    args=parser.parse_args(argv)
    from datetime import date
    try:
        asof=date.fromisoformat(args.as_of) if args.as_of else datetime.now(
            ZoneInfo("America/Los_Angeles")).date()
        snapshots=validated_csv(args.data_dir/"gem_historical_snapshots.csv",SNAPSHOT_FIELDS)
        bars=validated_csv(args.data_dir/"post_phase3_historical_adjusted_ohlcv.csv",BAR_FIELDS)
        report=calibrate(snapshots,bars,as_of=asof)
        research, meta=source_research_queue(args.data_dir)
    except (ValueError,OSError,UnicodeError,csv.Error) as exc:
        parser.error(str(exc))
    report["research_backfill"]=meta
    report["input_paths"]={
        "score_snapshots":"gem_historical_snapshots.csv",
        "verified_split_adjusted_prices":"post_phase3_historical_adjusted_ohlcv.csv",
    }
    report["live_weights_modified"]=False
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    write_rows(args.queue_output,QUEUE_COLUMNS,research)
    print(json.dumps({
        "status":report["status"],
        "historical_scored_trades":report["valid_completed_trades"],
        "research_leads_not_trades":len(research),
        "report":str(args.report),
        "queue":str(args.queue_output),
    }))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
