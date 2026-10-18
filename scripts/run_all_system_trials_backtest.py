#!/usr/bin/env python3
"""Audit ALL saved PDUFA/GEM/Pipeline trial records and replay audited historical trades.

This is a fail-closed audit, not an attempt to convert TODAY's GEM membership,
clinical trials registry records, or snapshots into historic trade evidence.
The pipeline scan summary is NOT equivalent to an accessible per-trial file.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from gem_historical_signal_backtest import (  # noqa E402
    RETURN_FIELDS, SUMMARY_FIELDS, TRADE_FIELDS, read_csv, run
)
from post_phase3_trade_backtest import bars_by_ticker, day, validate_event  # noqa E402

AUDIT_FIELDS=(
    "source","source_row","event_key","ticker","nct_id","drug",
    "pdufa_date","stage","stage_membership","disclosure_status",
    "historical_backtest_status","blocker",
)
SOURCES={
    "PDUFA":"pdufa_candidates.csv",
    "DISCOVERY":"discovery_events.csv",
    "POST_PHASE3_DISCOVERY":"post_phase3_discoveries.csv",
    "PHASE_PIPELINE":"phase_pipeline.csv",
    "ALL_PHASE_TRIALS":"all_phase_trials.csv",
}


def safe_dict(row):
    return {str(k):str(v or "").strip() for k,v in row.items() if k is not None}


def trial_rows(data_dir):
    result=[]
    for source,filename in SOURCES.items():
        path=Path(data_dir)/filename
        rows=read_csv(path)
        for i,record in enumerate(rows,1):
            row=safe_dict(record)
            key=row.get("event_key") or row.get("discovery_key") or ""
            ticker=row.get("ticker","").upper()
            nct=row.get("nct_id","")
            # If source has no exact program identity, do not infer GEM pass.
            if not key:
                key=(f"UNRESOLVED|{source}|{i}")
            result.append(dict(source=source,source_row=i,event_key=key,
                               ticker=ticker,nct_id=nct,
                               drug=row.get("drug") or row.get("intervention") or "",
                               pdufa_date=row.get("pdufa_date",""),
                               stage="",stage_membership="",
                               disclosure_status=row.get("pdufa_confirmation",""),
                               historical_backtest_status="NOT_EVALUATED",
                               blocker=""))
    membership_path=Path(data_dir)/"gem_stage_membership.json"
    try:
        membership=json.loads(membership_path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError):
        membership={}
    stage_entries=[]
    for stage,record in (membership.get("stages") or {}).items():
        for key,e in (record.get("entries") or {}).items():
            if not isinstance(e,dict):
                continue
            event_key=e.get("exact_program") or ""
            stage_entries.append((stage,key,e))
            # Existing PDUFA record can be a different exact program/indication.
            # Match exact_program only, never ticker alone.
            match=[r for r in result
                   if r["source"]=="PDUFA" and
                   r["event_key"]==event_key and event_key]
            if match:
                for r in match:
                    r["stage"]=stage
                    r["stage_membership"]=e.get("status","")
            else:
                result.append(dict(
                    source="GEM_MEMBERSHIP",source_row=len(stage_entries),
                    event_key=event_key or key,
                    ticker=str(e.get("ticker") or "").upper(),
                    nct_id=e.get("nct_id") or "",
                    drug=e.get("drug") or "",
                    pdufa_date=e.get("pdufa_date") or "",
                    stage=stage,
                    stage_membership=e.get("status") or "",
                    disclosure_status="",
                    historical_backtest_status="NOT_EVALUATED",
                    blocker=""))
    return result,stage_entries


def audit(data_dir, *, as_of=date(2026,10,18)):
    data_dir=Path(data_dir)
    cohort, stages=trial_rows(data_dir)
    events=read_csv(data_dir/"post_phase3_historical_trade_events.csv")
    bars=read_csv(data_dir/"post_phase3_historical_adjusted_ohlcv.csv")
    keyed={}
    duplicates=set()
    for event in events:
        k=event.get("event_key","")
        if k in keyed:
            duplicates.add(k)
        keyed[k]=event
    validated_bars, invalid_price_tickers=bars_by_ticker(bars)
    statuses=Counter()
    for row in cohort:
        key=row["event_key"]
        dated=day(row["pdufa_date"])
        if row["source"] in ("ALL_PHASE_TRIALS","PHASE_PIPELINE",
                              "DISCOVERY","POST_PHASE3_DISCOVERY") and not dated:
            blocker="NO_VERIFIED_PDUFA_DATE_OR_NONAPPLICATION_TRIAL"
        elif dated and dated>as_of:
            blocker="FUTURE_PDUFA_NOT_COMPLETED"
        elif not row["ticker"]:
            blocker="NO_EXACT_PUBLIC_TICKER"
        elif key in duplicates:
            blocker="DUPLICATE_HISTORICAL_EVENT_KEY"
        elif key not in keyed:
            blocker="MISSING_AUDITED_HISTORICAL_EVENT"
        else:
            event=keyed[key]
            reason,verified=validate_event(event)
            if reason:
                blocker=reason
            elif verified["pdufa_date"]>as_of:
                blocker="FUTURE_PDUFA_NOT_COMPLETED"
            elif row["ticker"] in invalid_price_tickers:
                blocker="INVALID_OR_DUPLICATE_ADJUSTED_OHLCV"
            elif not validated_bars.get(row["ticker"]):
                blocker="MISSING_VERIFIED_ADJUSTED_OHLCV"
            else:
                blocker="READY_FOR_REPLAY_ONLY_NEEDS_FULL_DATA_AUDIT"
        row["historical_backtest_status"]=(
            "POTENTIAL_REPLAY_INPUT" if blocker==
            "READY_FOR_REPLAY_ONLY_NEEDS_FULL_DATA_AUDIT" else "BLOCKED")
        row["blocker"]=blocker
        statuses[blocker]+=1

    # Run exactly the same 54 experimental settings on ALL (past) verified
    # audited events, not today's unverified trial rows. 2026 cap stays OFF.
    trades,summary,engine=run(events,bars,year=None,as_of=as_of,
                              market_caps=None)
    try:
        scan=json.loads((data_dir/"phase_pipeline_state.json").read_text(
            encoding="utf-8"))
    except (OSError,UnicodeError,ValueError):
        scan={}
    source_sizes={key:len(read_csv(data_dir/filename))
                  for key,filename in SOURCES.items()}
    pipeline_claim=int(scan.get("stored_trials") or 0)
    trial_rows_present=source_sizes.get("ALL_PHASE_TRIALS",0)
    pipeline_file_rows=source_sizes.get("PHASE_PIPELINE",0)
    summary_report={
        "as_of":as_of.isoformat(),
        "coverage_scope":"ALL_SAVED_TRIAL_SOURCES",
        "market_cap_filter_active":False,
        "scan_reported_stored_trials":pipeline_claim,
        "all_phase_trials_file_rows":trial_rows_present,
        "phase_pipeline_file_rows":pipeline_file_rows,
        "unavailable_scanned_trial_rows":max(0,pipeline_claim-pipeline_file_rows),
        "scan_reported_studies_scanned":scan.get("studies_scanned"),
        "scan_reported_registry_companies":scan.get("registry_companies"),
        "source_row_counts":source_sizes,
        "gem_stage_membership_counts":dict(Counter(
            stage for stage,_,e in stages if e.get("status")=="ACTIVE")),
        "gem_membership_entries_total":len(stages),
        "audited_saved_rows":len(cohort),
        "blocked_saved_rows":sum(r["historical_backtest_status"]=="BLOCKED"
                                 for r in cohort),
        "saved_rows_potential_replay_input":sum(
            r["historical_backtest_status"]=="POTENTIAL_REPLAY_INPUT"
            for r in cohort),
        "blocker_counts":dict(statuses),
        "historical_event_rows":len(events),
        "historical_price_rows":len(bars),
        "technical_grid_scenarios_per_event":engine["variants"],
        "completed_hypothetical_trade_scenarios":engine["completed_trades"],
        "unique_event_keys_with_completed_trades":engine.get(
            "unique_event_keys_with_completed_scenarios",0),
        "hypothetical_returns_calculated":bool(engine["completed_trades"]),
        "returns_prospectively_validated":False,
        "validated_win_rate_available":False,
        "status":"NOT_BACKTESTABLE_FROM_SAVED_DATA" if
            not engine["completed_trades"] else "EXPLORATORY_BACKTEST_NOT_VALIDATED",
        "restrictions":[
            "The scan count is not a readable trial dataset: missing source rows cannot be assumed to pass or fail trading screens.",
            "Present-day membership does not establish historic membership or public knowledge dates.",
            "Phase 2/3 studies without an original PDUFA target are not PDUFA return trades.",
            "Source-verified Phase 3 readout, two completed post-readout financing disclosures and original FDA goal are mandatory.",
            "Only audited split-adjusted daily OHLCV can yield a tradable hypothetical fill.",
            "The current 2026 study ignores the market-cap screen.",
            "No brokerage orders are submitted and no live scanner configuration is changed.",
        ]
    }
    return cohort,trades,summary,summary_report


def write_csv(path,fields,rows):
    with Path(path).open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir",type=Path,default=ROOT/"data")
    p.add_argument("--as-of",default="2026-10-18")
    p.add_argument("--output-dir",type=Path,
                   default=ROOT/"output"/"gem_all_trial_research_audit")
    args=p.parse_args(argv)
    as_of=day(args.as_of)
    if not as_of:
        p.error("--as-of must be an ISO YYYY-MM-DD date")
    records,trades,summary,audit_report=audit(args.data_dir,as_of=as_of)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    write_csv(args.output_dir/"every_saved_trial_eligibility.csv",
              AUDIT_FIELDS,records)
    priority=[
        dict(row, research_priority=(
            "P1_PAST_DECISION_SOURCE_BACKFILL" if
            row["blocker"]=="MISSING_AUDITED_HISTORICAL_EVENT" else
            "P2_FUTURE_PDUFA_TRACK_NOT_BACKTESTABLE_YET"))
        for row in records if row["blocker"] in (
            "MISSING_AUDITED_HISTORICAL_EVENT","FUTURE_PDUFA_NOT_COMPLETED")
    ]
    priority.sort(key=lambda x: (
        x["research_priority"], x["pdufa_date"],
        x["ticker"], x["event_key"]))
    write_csv(args.output_dir/"pdufa_historical_backfill_priorities.csv",
              ("research_priority",)+AUDIT_FIELDS,priority)
    write_csv(args.output_dir/"qualified_historical_trade_scenarios.csv",
              TRADE_FIELDS,trades)
    write_csv(args.output_dir/"entry_exit_returns.csv",RETURN_FIELDS,trades)
    write_csv(args.output_dir/"strategy_grid_summary.csv",SUMMARY_FIELDS,summary)
    audit_report["historical_backfill_priority_rows"]=len(priority)
    (args.output_dir/"coverage_and_blockers.json").write_text(
        json.dumps(audit_report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(audit_report,sort_keys=True))
    return 0


if __name__=="__main__":
    sys.exit(main())
