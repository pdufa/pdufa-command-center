"""Alpaca: read-only, split-adjusted EOD data and GEM/JR technical monitoring.

Authoritative clinical/financing event checks are separate from Alpaca prices.
A technical preview is NEVER a verified investment recommendation or an order.
No POST/PATCH/DELETE broker requests are made here.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from statistics import mean
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from post_phase3_trade_backtest import validate_event

ET=ZoneInfo("America/New_York")
DATA_URL="https://data.alpaca.markets/v2/stocks"
PAPER_URL="https://paper-api.alpaca.markets"
SYMBOL=re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")
ALERTS=("ENTRY_SETUP_RECHECK","ENTRY_REVIEW_IEX","WAIT",
        "ENTRY_BLOCKED","STAY_REVIEW","EXIT_WARNING","DATA_BLOCKED")


def paper_keys(env=None):
    env=os.environ if env is None else env
    if str(env.get("ALPACA_PAPER","")).lower()!="true":
        raise ValueError("Alpaca PAPER mode required; live brokerage disabled")
    key=env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID")
    secret=env.get("ALPACA_SECRET_KEY") or env.get("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise ValueError("Alpaca PAPER credentials missing from runner secrets")
    return str(key),str(secret)


def completed_session(now=None):
    """Read only sessions known to be complete, from 5pm ET onward."""
    t=(now or datetime.now(ET)).astimezone(ET)
    target=t.date() if t.hour>=17 else t.date()-timedelta(days=1)
    while target.weekday()>4:
        target-=timedelta(days=1)
    return target


def programs_from_membership(path="data/gem_stage_membership.json"):
    """Return all active exact programs; de-duplicate tickers only for API GETs."""
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,ValueError,UnicodeError):
        return []
    result=[]
    for stage in ("GEM","GEM_JR"):
        for key,x in (data.get("stages",{}).get(stage,{})
                      .get("entries",{})).items():
            if not isinstance(x,dict) or x.get("status")!="ACTIVE":
                continue
            ticker=str(x.get("ticker") or "").strip().upper()
            if not SYMBOL.fullmatch(ticker):
                continue
            result.append({
                "stage":stage,"ticker":ticker,
                "exact_program":x.get("exact_program") or key,
                "pdufa_date":x.get("pdufa_date") or "",
                "drug":x.get("drug") or ""})
    return result


def read_historical_events(path="data/post_phase3_historical_trade_events.csv"):
    try:
        with Path(path).open(encoding="utf-8",newline="") as f:
            return list(csv.DictReader(f))
    except (OSError,UnicodeError):
        return []


def _get_json(url,keys,*,opener=None):
    opener=opener or urlopen
    req=Request(url,method="GET",headers={
        "APCA-API-KEY-ID":keys[0],"APCA-API-SECRET-KEY":keys[1],
        "Accept":"application/json"})
    try:
        with opener(req,timeout=30) as response:
            return json.load(response)
    except HTTPError as exc:
        raise ValueError("Alpaca API HTTP "+str(exc.code)) from None
    except (URLError,TimeoutError):
        raise ValueError("Alpaca connection unavailable") from None
    except (TypeError,ValueError):
        raise ValueError("Invalid Alpaca response") from None


def alpaca_daily_bars(symbol,keys,*,as_of=None,feed="sip",opener=None):
    """Request all split-adjusted bars, paginate, enforce complete sessions."""
    ticker=str(symbol).upper().strip()
    if not SYMBOL.fullmatch(ticker) or feed not in ("sip","iex"):
        raise ValueError("Invalid symbol or Alpaca feed")
    cutoff=as_of or completed_session()
    start=cutoff-timedelta(days=260)
    if cutoff>date.today()+timedelta(days=1):
        raise ValueError("Invalid future as-of date")
    path=DATA_URL+"/"+quote(ticker,safe="")+"/bars"
    allbars=[]
    token=None
    seen=set()
    for _ in range(30):
        params={"timeframe":"1Day","start":start.isoformat(),
                "end":(cutoff+timedelta(days=1)).isoformat(),
                "feed":feed,"adjustment":"split","asof":cutoff.isoformat(),
                "limit":10000}
        if token:
            params["page_token"]=token
        payload=_get_json(path+"?"+urlencode(params),keys,opener=opener)
        if not isinstance(payload,dict) or not isinstance(payload.get("bars"),list):
            raise ValueError("Alpaca returned no valid bar array")
        for x in payload["bars"]:
            try:
                d=date.fromisoformat(str(x["t"])[:10])
                o,h,l,c,v=(float(x[k]) for k in ("o","h","l","c","v"))
            except (KeyError,TypeError,ValueError):
                raise ValueError("Malformed OHLCV bar") from None
            if (d>cutoff or d<start or d.weekday()>4 or
                not all(math.isfinite(z) for z in (o,h,l,c,v)) or
                min(o,h,l,c,v)<=0 or h<max(o,c) or l>min(o,c) or h<l):
                raise ValueError("Invalid or incomplete market bar")
            allbars.append({"session":d,"open":o,"high":h,
                            "low":l,"close":c,"volume":v})
        token=payload.get("next_page_token")
        if not token:
            break
        if token in seen:
            raise ValueError("Repeated market pagination token")
        seen.add(token)
    else:
        raise ValueError("Market pagination exceeded safety limit")
    allbars.sort(key=lambda x:x["session"])
    if len({x["session"] for x in allbars})!=len(allbars):
        raise ValueError("Duplicate Alpaca session")
    if any((allbars[i]["session"]-allbars[i-1]["session"]).days>7
           for i in range(1,len(allbars))):
        raise ValueError("Unreconciled missing price sessions")
    return allbars


def paper_positions(keys,*,opener=None):
    """Read-only paper positions; no account numbers or order IDs returned."""
    raw=_get_json(PAPER_URL+"/v2/positions",keys,opener=opener)
    if not isinstance(raw,list):
        raise ValueError("Invalid paper-position response")
    result={}
    for x in raw:
        if not isinstance(x,dict):
            continue
        sym=str(x.get("symbol") or "").upper()
        try:
            qty=float(x.get("qty",0))
        except (ValueError,TypeError):
            continue
        if SYMBOL.fullmatch(sym) and math.isfinite(qty) and qty>0:
            result[sym]={"held":True,"avg_entry":x.get("avg_entry_price")}
    return result


def rsi14(bars):
    if len(bars)<15:
        return None
    c=[b["close"] for b in bars]
    gains=[max(c[i]-c[i-1],0) for i in range(1,len(c))]
    losses=[max(c[i-1]-c[i],0) for i in range(1,len(c))]
    avg_g=mean(gains[:14]);avg_l=mean(losses[:14])
    for gain,loss in zip(gains[14:],losses[14:]):
        avg_g=(avg_g*13+gain)/14
        avg_l=(avg_l*13+loss)/14
    if avg_l==0:
        return 100.0 if avg_g else 50.0
    return round(100-100/(1+avg_g/avg_l),2)


def technical_snapshot(bars):
    if len(bars)<51:
        return None
    now=bars[-1];previous=bars[-2]
    sma20=mean(x["close"] for x in bars[-20:])
    prev_sma20=mean(x["close"] for x in bars[-21:-1])
    sma50=mean(x["close"] for x in bars[-50:])
    true_ranges=[]
    for i in range(len(bars)-14,len(bars)):
        x,pc=bars[i],bars[i-1]["close"]
        true_ranges.append(max(x["high"]-x["low"],
                               abs(x["high"]-pc),abs(x["low"]-pc)))
    atr=mean(true_ranges)
    base=bars[-11:-1]
    base_high=max(x["high"] for x in base)
    base_low=min(x["low"] for x in base)
    average_vol=mean(x["volume"] for x in bars[-21:-1])
    rvol=now["volume"]/average_vol if average_vol>0 else None
    dollar_liq=mean(x["close"]*x["volume"] for x in bars[-21:-1])
    stop=base_low-.25*atr
    risk_pct=100*(now["close"]-stop)/now["close"] if stop>0 else None
    return {
        "as_of":now["session"].isoformat(),
        "close":round(now["close"],4),
        "sma20":round(sma20,4),"sma50":round(sma50,4),
        "rsi14":rsi14(bars),"atr14":round(atr,4),
        "rvol20":round(rvol,3) if rvol is not None else None,
        "prior20_dollar_liquidity":round(dollar_liq,2),
        "base_high":round(base_high,4),"base_low":round(base_low,4),
        "base_atr_width":round((base_high-base_low)/atr,3) if atr>0 else None,
        "provisional_stop":round(stop,4),
        "provisional_risk_pct":round(risk_pct,3) if risk_pct is not None else None,
        "breakout":bool(atr>0 and now["close"]>=base_high+.1*atr),
        "trend":bool(now["close"]>=sma20>=sma50),
        "two_closes_below_sma20":bool(
            now["close"]<sma20 and previous["close"]<prev_sma20),
        "stale":False}


def assess(ticker,bars,events,*,positions=None,as_of=None,feed="sip"):
    cutoff=as_of or completed_session()
    result={"ticker":ticker,"provider":"ALPACA","feed":feed,
            "data_adjustment":"split","is_read_only":True,
            "market_cap_filter_active":False,
            "signal":"DATA_BLOCKED","reason":"INSUFFICIENT_OR_STALE_HISTORY"}
    if len(bars)<51 or (cutoff-bars[-1]["session"]).days>6:
        return result
    m=technical_snapshot(bars)
    if m is None:
        return result
    result["metrics"]=m
    own=positions is not None and ticker in positions
    relevant=[r for r in events if str(r.get("ticker") or "").strip().upper()==ticker]
    qualified=[]
    for ev in relevant:
        reason,dates=validate_event(ev)
        if not reason and dates["phase3_public_date"]<=cutoff and (
            dates["second_financing_public_date"]<=cutoff):
            qualified.append((ev,dates))
    if own:
        result["signal"]="STAY_REVIEW"
        result["reason"]="NO_PROGRAMMED_EXIT_WARNING"
        result["paper_position"]=True
        result["position_scope"]="ALPACA_PAPER_ONLY"
        if m["two_closes_below_sma20"]:
            result.update(signal="EXIT_WARNING",reason="TWO_CLOSES_BELOW_SMA20")
        elif len(qualified)==1 and (
             qualified[0][1]["pdufa_date"]-cutoff).days<=3:
            result.update(signal="EXIT_WARNING",reason="PDUFA_CUTOFF")
        return result
    result["paper_position"]=False if positions is not None else None
    result["position_scope"]="ALPACA_PAPER_ONLY" if positions is not None else "UNVERIFIED"
    if len(qualified)!=1:
        result.update(signal="ENTRY_BLOCKED",
                      reason="PHASE3_TWO_FINANCINGS_AND_PDUFA_NOT_ALL_VERIFIED")
        return result
    _,dates=qualified[0]
    rem=(dates["pdufa_date"]-cutoff).days
    sessions=sum(dates["second_financing_public_date"]<b["session"]<=cutoff for b in bars)
    risk_ok=(m["provisional_risk_pct"] is not None and
             0<m["provisional_risk_pct"]<=8 and
             0.5*m["atr14"]<=(m["close"]-m["provisional_stop"])<=3*m["atr14"])
    score=(25 if m["trend"] else 0)+(20 if (m["rvol20"] or 0)>=1.5 else 10)+(
        20 if m["breakout"] else 0)+(20 if risk_ok else 0)+(
        15 if 14<=rem<=120 else 8)
    result["entry_score_preview"]=score
    result["days_to_pdufa"]=rem
    conditions=(sessions>=10 and 7<=rem<=180 and
                m["base_atr_width"] is not None and m["base_atr_width"]<=3 and
                m["breakout"] and (m["rvol20"] or 0)>=1.5 and
                m["prior20_dollar_liquidity"]>=250000 and risk_ok and score>=70)
    if not conditions:
        result.update(signal="WAIT",reason="TECHNICAL_OR_RISK_CONDITION_INCOMPLETE")
    elif feed=="sip":
        result.update(signal="ENTRY_SETUP_RECHECK",
                      reason="CHECK_NEXT_OPEN_GAP_AND_RISK_NO_BUY_ORDER")
    else:
        result.update(signal="ENTRY_REVIEW_IEX",
                      reason="SINGLE_EXCHANGE_VOLUME_NOT_FULL_MARKET")
    return result


def get_symbol_report(ticker,keys,events,*,positions=None,
                      feed="sip",as_of=None,opener=None):
    cutoff=as_of or completed_session()
    bars=alpaca_daily_bars(ticker,keys,as_of=cutoff,feed=feed,opener=opener)
    result=assess(ticker,bars,events,positions=positions,feed=feed,as_of=cutoff)
    result["bars"]=len(bars)
    return result


def render_alpaca_panel(stage,root="data"):
    """On-demand per-ticker Alpaca data for each GEM/JR dashboard. Never an order."""
    import streamlit as st
    from alpaca_connection import load_paper_credentials
    stage_code="GEM_JR" if stage in ("GEM JR","GEM_JR") else "GEM"
    candidates=[x for x in programs_from_membership(
        Path(root)/"gem_stage_membership.json") if x["stage"]==stage_code]
    title="GEM JR" if stage_code=="GEM_JR" else "GEM"
    with st.expander("ALPACA DATA & ENTRY / STAY / EXIT — "+title,
                     expanded=False):
        st.caption("Alpaca is the selected technical-data source; historical "
                   "split-adjusted daily OHLCV, not intraday execution quotes. "
                   "No trades are placed. Scores remain unvalidated.")
        if not candidates:
            st.info("No active candidates in this GEM stage.")
            return
        keys,problem=load_paper_credentials(st.secrets)
        if problem:
            st.warning(problem)
            st.caption("Configure Alpaca PAPER keys in Streamlit app Secrets; never paste keys here.")
            return
        symbol=st.selectbox("Ticker",sorted({r["ticker"] for r in candidates}),
                            key="alpaca_select_"+stage_code)
        feed=st.selectbox("Provider feed",["sip","iex"],
                          format_func=lambda x:("Consolidated SIP EOD" if x=="sip"
                                               else "IEX only — review"),
                          key="alpaca_feed_"+stage_code)
        if st.button("REFRESH ALPACA SIGNAL",key="alpaca_refresh_"+stage_code):
            try:
                # Only paper positions are read; never infer live broker holdings.
                try:
                    positions=paper_positions(keys)
                except (ValueError,RuntimeError):
                    positions=None
                report=get_symbol_report(symbol,keys,read_historical_events(
                    Path(root)/"post_phase3_historical_trade_events.csv"),
                    positions=positions,feed=feed)
            except (ValueError,RuntimeError,OSError,TypeError):
                report={"ticker":symbol,"feed":feed,
                        "signal":"DATA_BLOCKED",
                        "reason":"ALPACA_ACCESS_OR_HISTORY_ERROR"}
            st.session_state["_alpaca_"+stage_code]=report
        report=st.session_state.get("_alpaca_"+stage_code)
        if not report or report.get("ticker")!=symbol or report.get("feed")!=feed:
            st.info("Select a ticker and click refresh to retrieve its Alpaca indicators.")
            return
        signal=report.get("signal","DATA_BLOCKED")
        if signal=="ENTRY_SETUP_RECHECK":
            st.warning("ENTRY SETUP — Next-open gap/risk verification required. Not an order.")
        elif signal=="EXIT_WARNING":
            st.error("EXIT WARNING — Paper position only.")
        else:
            st.info(f"{signal}: {report.get('reason','')}")
        m=report.get("metrics") or {}
        if m:
            a,b,c,d=st.columns(4)
            a.metric("Close",m.get("close"))
            b.metric("SMA20",m.get("sma20"))
            c.metric("ATR14",m.get("atr14"))
            d.metric("RVOL20",m.get("rvol20"))
            st.caption(f"Date: {m['as_of']} | SMA50: {m['sma50']} | RSI14: {m['rsi14']} | "
                       f"Base: {m['base_low']}–{m['base_high']} | "
                       f"Provisional stop: {m['provisional_stop']} | "
                       f"Entry score preview: {report.get('entry_score_preview','N/A')} | "
                       f"Feed: {feed.upper()}")
        st.caption("STAY/EXIT requires an actual recorded position and valid "
                   "clinical/deadline evidence. A missing benchmark is not a failed "
                   "technical BUY; it means no verified recommendation is possible.")
