#!/usr/bin/env python3
"""Research-only post-close Alpaca GEM entry / paper-position exit monitor.

Alpaca watchlist and position APIs are GET-only here. The ONLY operation
adding symbols exists in separate operator-invoked alpaca_gem_watchlist.py.
No orders. No future-informed buy fills. Verified clinical and financing
benchmarks are required for an ENTRY SETUP; otherwise evidence stays REVIEW.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from gem_historical_signal_backtest import atr_at
from post_phase3_trade_backtest import day, validate_event
from scripts.alpaca_gem_watchlist import (
    PAPER_URL, DEFAULT_NAME, AlpacaUnavailable, get_watchlist, paper_credentials
)
from scripts.fetch_gem_2025_alpaca_review import request_bars

def positions_readonly(credentials, opener=None):
    request=Request(PAPER_URL+"/v2/positions",method="GET",headers={
        "APCA-API-KEY-ID":credentials[0],
        "APCA-API-SECRET-KEY":credentials[1],
        "Accept":"application/json"
    })
    fetch=opener or urlopen
    try:
        with fetch(request,timeout=25) as res:
            records=json.load(res)
        if not isinstance(records,list):
            raise AlpacaUnavailable("Unexpected paper-position response")
        return {str(x.get("symbol","")).upper():x
                for x in records if isinstance(x,dict)}
    except HTTPError as exc:
        raise AlpacaUnavailable(
            f"Alpaca paper positions request returned HTTP {exc.code}") from None
    except (URLError,TimeoutError):
        raise AlpacaUnavailable("Alpaca paper positions not reachable") from None


def clean_bars(input_bars):
    """No false indicator signals from duplicated, missing or broken bars."""
    out=[]
    for r in input_bars:
        try:
            timestamp=day(r.get("session"))
            o,h,l,c,v=(float(r.get(k)) for k in
                       ("open","high","low","close","volume"))
        except (ValueError, TypeError):
            return []
        if (not timestamp or not all(math.isfinite(x) for x in (o,h,l,c,v))
                or min(o,h,l,c,v)<=0 or l>min(o,c) or h<max(o,c)
                or l>h):
            return []
        out.append({"session":timestamp,"open":o,"high":h,
                    "low":l,"close":c,"volume":v})
    out.sort(key=lambda x:x["session"])
    if len(out)<50 or len(set(x["session"] for x in out)) != len(out):
        return []
    if any((out[i]["session"]-out[i-1]["session"]).days>7
           for i in range(1,len(out))):
        return []
    return out


def market_snapshot(bars):
    i=len(bars)-1
    if i<50:
        return None
    current=bars[i]
    atr=atr_at(bars,i,14)
    if not atr or atr<=0:
        return None
    lookback=bars[i-10:i]
    high=max(x["high"] for x in lookback)
    low=min(x["low"] for x in lookback)
    volume_prior20=mean(x["volume"] for x in bars[i-20:i])
    dollar_prior20=mean(x["close"]*x["volume"] for x in bars[i-20:i])
    sma20=mean(x["close"] for x in bars[i-19:i+1])
    sma50=mean(x["close"] for x in bars[i-49:i+1])
    prev_sma20=mean(x["close"] for x in bars[i-20:i])
    rvol=current["volume"]/volume_prior20 if volume_prior20 else 0
    stop=low-.25*atr
    breakout=(current["close"]>=high+.1*atr)
    tight_base=(high-low<=3*atr)
    trend=(current["close"]>=sma20>=sma50)
    stop_risk=(0.5*atr<=current["close"]-stop<=3*atr
               and (current["close"]-stop)/current["close"]<=.08)
    return {
        "close":round(current["close"],4),
        "date":current["session"].isoformat(),
        "atr14":round(atr,4),
        "sma20":round(sma20,4),
        "sma50":round(sma50,4),
        "rvol20":round(rvol,3),
        "prior20_avg_dollar_volume":round(dollar_prior20,2),
        "base_high":round(high,4),
        "base_low":round(low,4),
        "provisional_stop":round(stop,4),
        "trend":trend,
        "tight_base":tight_base,
        "breakout":breakout,
        "stop_risk_ok_at_close":stop_risk,
        "liquidity_ok":dollar_prior20>=250000,
        "two_closes_below_sma20":(
            current["close"]<sma20 and bars[i-1]["close"]<prev_sma20),
    }


def evaluate(symbol,bars,events,positions,*,today,feed="iex"):
    """Generate an alert from data available at the previous completed session."""
    record={"ticker":symbol,"feed":feed,"scan_date":today.isoformat(),
            "not_order_instruction":True,
            "stage":"REVIEW","alert":"NONE",
            "market_cap_filter_active":False}
    candles=clean_bars(bars)
    if not candles:
        record.update(stage="DATA_BLOCKED",reason="INADEQUATE_OR_INVALID_OHLCV")
        return record
    latest=candles[-1]["session"]
    if (today-latest).days<0 or (today-latest).days>4:
        record.update(stage="DATA_BLOCKED",reason="STALE_OR_FUTURE_MARKET_BAR")
        return record
    # A 50-bar minimum is enforced; EOD signals never pretend next-open fill.
    snap=market_snapshot(candles)
    if not snap:
        record.update(stage="DATA_BLOCKED",reason="INDICATORS_UNAVAILABLE")
        return record
    record["technical"]=snap
    matched=[x for x in events if str(x.get("ticker","")).upper()==symbol]
    valid=[]
    for ev in matched:
        reason, dates=validate_event(ev)
        if not reason and dates["second_financing_public_date"]<=latest:
            valid.append((ev,dates))
    holding=positions.get(symbol)
    if holding:
        try:
            qty=float(holding.get("qty","0"))
        except (ValueError,TypeError):
            qty=0.0
        if qty>0:
            record["paper_position_present"]=True
            record["stage"]="PAPER_POSITION_MONITOR"
            record["paper_avg_entry_price"]=holding.get("avg_entry_price")
            record["exit_signal_basis"]="PAPER_POSITION_ONLY_NOT_EXTERNAL_BROKER"
            # No exact trailing ATR stop without original entry timestamp.
            record["trailing_stop"]="UNAVAILABLE_POSITION_ENTRY_DATE"
            due=any((d["pdufa_date"]-latest).days<=3
                    for _,d in valid)
            if due:
                record.update(alert="EXIT_WARNING",reason="PDUFA_MINUS_3_DAYS")
            elif snap["two_closes_below_sma20"]:
                record.update(alert="EXIT_WARNING",reason="TWO_CLOSES_BELOW_SMA20")
            else:
                record.update(alert="HOLD_REVIEW",
                              reason="NO_SMA20_OR_DEADLINE_EXIT_TRIGGER")
            return record
    record["paper_position_present"]=False
    record["stage"]="WATCHING_ENTRY"
    if len(valid)!=1:
        record.update(alert="ENTRY_BLOCKED",
                      reason="EXACT_PROGRAM_TWO_BENCHMARK_EVIDENCE_NOT_VERIFIED")
        return record
    ev,dated=valid[0]
    record["event_key"]=ev.get("event_key")
    time_to_pdufa=(dated["pdufa_date"]-latest).days
    post_financing=sum(
        dated["second_financing_public_date"] < x["session"] <= latest
        for x in candles)
    conditions=(post_financing>=10 and 7<=time_to_pdufa<=180
                and snap["tight_base"] and snap["breakout"]
                and snap["rvol20"]>=1.5 and snap["liquidity_ok"]
                and snap["stop_risk_ok_at_close"])
    score=((25 if snap["trend"] else 0)
           + (20 if snap["rvol20"]>=1.5 else 10)
           + (20 if snap["breakout"] else 0)
           + (20 if snap["stop_risk_ok_at_close"] else 0)
           + (15 if 14<=time_to_pdufa<=120 else 8))
    record["entry_score_preview"]=score
    record["entry_score_threshold"]=70
    record["days_to_pdufa"]=time_to_pdufa
    if not conditions or score<70:
        record.update(alert="WAIT",reason="ENTRY_REQUIREMENTS_NOT_ALL_MET")
    elif feed!="sip":
        record.update(alert="ENTRY_SETUP_REVIEW",
                      reason="IEX_VOLUME_NOT_CONSOLIDATED")
    else:
        record.update(alert="ENTRY_SETUP_NEXT_OPEN_RECHECK",
                      reason="SIGNAL_AT_CLOSE_ONLY_NO_TRADE_PLACED")
    return record


def collect(events, *, today, credentials, watchlist_name=DEFAULT_NAME,
            feed="sip", opener=None, data_fetch=None, symbols_override=None):
    if symbols_override is None:
        watchlist=get_watchlist(watchlist_name,credentials=credentials,opener=opener)
        if watchlist is None:
            raise AlpacaUnavailable("Named Alpaca paper watchlist does not exist")
        assets=watchlist.get("assets",[])
        if not isinstance(assets,list):
            raise AlpacaUnavailable("Alpaca returned invalid watchlist assets")
        symbols=sorted(set(str(a.get("symbol","")).strip().upper()
                           for a in assets if isinstance(a,dict)
                           and a.get("symbol")))
    else:
        from scripts.alpaca_gem_watchlist import SYMBOL
        if not isinstance(symbols_override,(list,tuple,set)):
            raise ValueError("Symbols override must be a list/set/tuple")
        symbols=sorted(set(str(x).upper().strip() for x in symbols_override))
        if len(symbols)>80 or any(not SYMBOL.fullmatch(x) for x in symbols):
            raise ValueError("Too many or invalid GEM tickers")
        watchlist_name="GEM_AND_GEM_JR_ACTIVE_MEMBERSHIP"
    positions=positions_readonly(credentials,opener=opener)
    output=[]
    for symbol in symbols:
        try:
            start=(today-timedelta(days=220)).isoformat()
            end=(today+timedelta(days=1)).isoformat()
            bars=request_bars(symbol,start,end,today.isoformat(),
                              credentials[0],credentials[1],
                              feed=feed,fetch=data_fetch)
            result=evaluate(symbol,bars,events,positions,today=today,feed=feed)
        except (ValueError,RuntimeError) as exc:
            # No secrets, full request headers, or account identifiers logged.
            result={"ticker":symbol,"stage":"DATA_BLOCKED","alert":"NONE",
                    "reason":"ALPACA_MARKET_DATA_UNAVAILABLE",
                    "market_cap_filter_active":False}
        output.append(result)
    return {"date":today.isoformat(),"watchlist_name":watchlist_name,
            "feed":feed,"read_only":True,"orders_submitted":0,
            "market_cap_filter_active":False,
            "tracked_symbols":len(symbols),"signals":output}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--universe",choices=["stages","watchlist"],default="stages",
                   help="Default: automatically scan all active GEM/JR tickers")
    p.add_argument("--stage-membership",default="data/gem_stage_membership.json")
    p.add_argument("--watchlist",default=DEFAULT_NAME)
    p.add_argument("--events",default="data/post_phase3_historical_trade_events.csv")
    p.add_argument("--feed",choices=["iex","sip"],default="sip")
    p.add_argument("--output",default="output/alpaca_gem_daily_monitor.json")
    args=p.parse_args(argv)
    today=datetime.now(ZoneInfo("America/New_York")).date()
    try:
        credentials=paper_credentials()
        with open(args.events,encoding="utf-8",newline="") as f:
            import csv
            events=list(csv.DictReader(f))
        if args.universe=="stages":
            from alpaca_gem_provider import active_stage_programs
            symbols=sorted({x["ticker"] for x in active_stage_programs(
                args.stage_membership)})
            if not symbols:
                raise AlpacaUnavailable("No active GEM or GEM JR tickers found")
        else:
            symbols=None
        report=collect(events,today=today,credentials=credentials,
                       watchlist_name=args.watchlist,feed=args.feed,
                       symbols_override=symbols)
        report["universe"]=args.universe
        path=Path(args.output)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                        encoding="utf-8")
        print(f"GEM daily monitor: {report['tracked_symbols']} symbols checked; "
              f"report {path}; no brokerage orders.")
        for r in report["signals"]:
            print(f"{r['ticker']} | {r['stage']} | {r['alert']} | "
                  f"{r.get('reason','')}")
        # We intentionally do not print account/position quantity or secret.
    except (OSError, AlpacaUnavailable, ValueError) as exc:
        p.exit(2,str(exc)+"\n")


if __name__=="__main__":
    main()
