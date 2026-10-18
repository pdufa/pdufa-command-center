"""Alpaca-only, evidence-gated STAY/EXIT monitor for PAPER positions.

The server never places orders. A current paper position is not evidence of
an external brokerage position. A two-close SMA20 exit and a verified
PDUFA-minus-3-day limit are warnings, not verified trading profits.
"""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .alpaca_market_chart import _credentials, ALPACA_HOST, SYMBOL
from .alpaca_entry_signal import history, session_context
from .gem_research_adapter import RESOLVED


def _day(x):
    try:
        return date.fromisoformat(str(x or "")[:10])
    except ValueError:
        return None


def paper_position(symbol):
    """Read only Alpaca paper GET /v2/positions/SYMBOL. No DELETE or POST."""
    if not SYMBOL.fullmatch(symbol):
        raise ValueError("Invalid ticker")
    keys=_credentials()
    if not keys:
        raise ValueError("Alpaca paper credentials not configured")
    req=Request("https://paper-api.alpaca.markets/v2/positions/"+
                quote(symbol,safe=""),method="GET",headers={
                "APCA-API-KEY-ID":keys[0],
                "APCA-API-SECRET-KEY":keys[1],"Accept":"application/json",
                "User-Agent":"PDUFA-Paper-Position-Monitor/1.0"})
    try:
        with urlopen(req,timeout=9) as r:
            raw=r.read(80_001)
        if len(raw)>80_000:
            raise ValueError("Paper position response oversized")
        payload=json.loads(raw)
    except HTTPError as e:
        if e.code==404:
            return None
        raise ValueError("Paper position API failed") from None
    except (OSError,URLError,TimeoutError,TypeError,ValueError):
        raise ValueError("Paper position source unavailable") from None
    if not isinstance(payload,dict) or str(payload.get("symbol","")).upper()!=symbol:
        raise ValueError("Wrong account symbol or invalid paper position")
    try:
        qty=float(payload.get("qty"))
        price=float(payload.get("avg_entry_price"))
    except (ValueError,TypeError):
        raise ValueError("Invalid paper position record") from None
    if not (math.isfinite(qty) and math.isfinite(price)
            and qty>0 and price>0):
        raise ValueError("Invalid long paper position")
    return {"exists":True,"avgEntry":round(price,4),
            "scope":"ALPACA_PAPER_ONLY"}


def technical_exit(bars,expected_sessions):
    """Calculate two below-SMA20 closes using consecutive exchange sessions."""
    if len(bars)<51 or [b["date"] for b in bars[-21:]]!=expected_sessions[-21:]:
        raise ValueError("Missing completed SIP daily sessions")
    p=bars[-2];current=bars[-1]
    sma_prev=sum(b["close"] for b in bars[-21:-1])/20
    sma_now=sum(b["close"] for b in bars[-20:])/20
    sma50=sum(b["close"] for b in bars[-50:])/50
    true_ranges=[]
    for prior,x in zip(bars[-16:-1],bars[-15:]):
        true_ranges.append(max(x["high"]-x["low"],
                               abs(x["high"]-prior["close"]),
                               abs(x["low"]-prior["close"])))
    atr=sum(true_ranges[-14:])/14
    return {
        "asOf":current["date"],"close":round(current["close"],4),
        "previousClose":round(p["close"],4),
        "sma20":round(sma_now,4),"sma50":round(sma50,4),
        "atr14":round(atr,4),
        "belowSma20TwoCloses":p["close"]<sma_prev and current["close"]<sma_now,
        "trailingStop":"UNAVAILABLE_WITHOUT_DATED_ENTRY_AND_STOP_LEDGER",
    }


def exit_for_program(exact_key,ticker,*,now=None):
    """Only server-resolved permanent program identity is allowed."""
    from .source_workspace import workspace
    from .wt_research import _context
    now=now or datetime.now(timezone.utc)
    response={
        "provider":"ALPACA","ticker":ticker,
        "status":"UNAVAILABLE","reason":"VERIFICATION_REQUIRED",
        "positionScope":"ALPACA_PAPER_ONLY","paperPosition":None,
        "readOnly":True,"orderExecutionEnabled":False,
        "marketFeed":"SIP_SPLIT_ADJUSTED_HISTORICAL",
        "validatedTradingStrategy":False,
        "checkedAt":now.isoformat()
    }
    try:
        if not SYMBOL.fullmatch(ticker):
            raise ValueError("Bad ticker")
        snap=workspace()
        members=[r for group in snap.get("members",{}).values()
                 for r in group.get("rows",[]) if
                 r.get("id")==exact_key and r.get("ticker")==ticker]
        if len(members)!=1:
            raise ValueError("Exact clinical program not uniquely resolved")
        row=members[0]
        # Paper positions do not imply user is trading at another brokerage.
        pos=paper_position(ticker)
        if pos is None:
            response.update(status="WAIT",reason="NO_ALPACA_PAPER_POSITION",
                            paperPosition=False)
            return response
        response["paperPosition"]=True
        response["paperAverageEntry"]=pos["avgEntry"]
        context=_context()
        event_key=str(row.get("eventKey") or "")
        event=context["events"].get(event_key,{}) if exact_key.startswith("APPLICATION|") else {}
        pdufa=_day(event.get("pdufa_date"))
        program_pdufa=_day(row.get("pdufaDate"))
        verified=bool(
            pdufa and pdufa==program_pdufa and
            str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
            and str(event.get("pdufa_evidence_url") or "").startswith("https://"))
        outcome=str(event.get("outcome") or "").upper()
        calendar=session_context(now)
        # A consistent SIP technical series; no IEX/SIP volume mixing.
        anchor=now.date()-timedelta(days=180)
        bars=history(ticker,anchor,calendar["expectedSession"],now)
        tech=technical_exit(bars,calendar["recentSessions"])
        response["technical"]=tech
        response["pdufaVerified"]=verified
        if verified:
            response["pdufaDate"]=pdufa.isoformat()
            response["daysToPdufa"]=(pdufa-now.date()).days
        if verified and (outcome in RESOLVED):
            response.update(status="EXIT_WARNING",reason="FDA_ACTION_RESOLVED_REVIEW")
        elif verified and (pdufa-now.date()).days<=3:
            response.update(status="EXIT_WARNING",reason="PDUFA_MINUS_THREE_DAYS")
        elif tech["belowSma20TwoCloses"]:
            response.update(status="EXIT_WARNING",reason="TWO_CLOSES_BELOW_SMA20")
        elif not verified:
            response.update(status="STAY_REVIEW",reason="PDUFA_NOT_VERIFIED_SO_NO_SCHEDULED_EXIT")
        else:
            response.update(status="STAY",reason="NO_PROGRAMMED_EXIT_WARNING")
    except (ValueError,KeyError,TypeError,OverflowError,OSError,ImportError):
        response.update(status="UNAVAILABLE",reason="PAPER_OR_SIP_OR_EXACT_PROGRAM_DATA_UNAVAILABLE")
    return response
