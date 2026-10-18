#!/usr/bin/env python3
"""After-close read-only Alpaca EOD technical scan for every active GEM/JR symbol."""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from alpaca_data_provider import (
    paper_keys, completed_session, programs_from_membership,
    read_historical_events, paper_positions, get_symbol_report
)


def scan(*,membership,events,credentials,feed="sip",as_of=None,
         get_report=get_symbol_report,positions=None):
    today=as_of or completed_session()
    programs=programs_from_membership(membership)
    if not programs:
        raise ValueError("No active GEM/GEM JR programs available")
    symbols=sorted({p["ticker"] for p in programs})
    if len(symbols)>80:
        raise ValueError("Unusually large GEM symbol universe")
    report=[]
    for symbol in symbols:
        try:
            result=get_report(symbol,credentials,events,
                              positions=positions,feed=feed,as_of=today)
        except (ValueError,RuntimeError,OSError,TypeError):
            result={"ticker":symbol,"provider":"ALPACA","feed":feed,
                    "signal":"DATA_BLOCKED","reason":"MARKET_DATA_FAILED"}
        result["stages"]=sorted({p["stage"] for p in programs
                                  if p["ticker"]==symbol})
        report.append(result)
    return {"report_date":today.isoformat(),"provider":"ALPACA",
            "requested_feed":feed,"split_adjusted":True,"read_only":True,
            "orders_placed":0,"active_programs":len(programs),
            "unique_tickers":len(symbols),
            "data_blocked":sum(x.get("signal")=="DATA_BLOCKED" for x in report),
            "report":report}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--membership",default="data/gem_stage_membership.json")
    p.add_argument("--events",default="data/post_phase3_historical_trade_events.csv")
    p.add_argument("--output",default="output/alpaca_gem_eod.json")
    p.add_argument("--feed",choices=["sip","iex"],default="sip")
    args=p.parse_args(argv)
    try:
        credentials=paper_keys()
        paper=paper_positions(credentials)
        report=scan(membership=args.membership,
                    events=read_historical_events(args.events),
                    credentials=credentials,feed=args.feed,positions=paper)
        output=Path(args.output)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",
                          encoding="utf-8")
        print("Alpaca EOD data scan:",report["unique_tickers"],
              "tickers,",report["data_blocked"],"market-data blocked; no orders")
        for item in report["report"]:
            print(item["ticker"],item["signal"],item.get("reason",""))
    except (ValueError,OSError,RuntimeError) as exc:
        # Do not print HTTP headers, any broker account fields or credentials.
        print("Alpaca monitoring could not run:",str(exc),file=sys.stderr)
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
