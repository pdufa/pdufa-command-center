"""Alpaca technical observations for choosing which clinical trial programs to research.

No broker positions, trading orders, exact-program scoring, or synthetic bars.
One ticker can represent several distinct trial programs: clinical eligibility
is always displayed separately from these issuer-level market indicators.
"""
from __future__ import annotations

import math
import threading
import time
from datetime import datetime, timedelta, timezone
from statistics import mean
from urllib.parse import quote

from .alpaca_entry_signal import _request, history, session_context
from .alpaca_market_chart import SYMBOL

_CACHE = {}
_LOCK = threading.Lock()
VALID_FEEDS = ("sip", "iex")


def _get_daily(ticker, feed, now, calendar):
    expected = calendar["expectedSession"]
    if feed == "sip":
        # Already performs split adjustment, uses delayed consolidated history,
        # rejects pagination and skips bars after the completed session.
        return history(ticker, now.date()-timedelta(days=105), expected, now)
    # The IEX feed is a distinctly labeled single-exchange fallback, NOT
    # substituted into a consolidated SIP-volume BUY rule.
    payload = _request("/v2/stocks/"+quote(ticker, safe="")+"/bars", {
        "timeframe":"1Day",
        "start":(now.date()-timedelta(days=180)).isoformat(),
        "end":(now-timedelta(minutes=16)).isoformat(),
        "limit":10000, "adjustment":"split", "feed":"iex", "sort":"asc",
    })
    if not isinstance(payload,dict) or not isinstance(payload.get("bars"),list) or payload.get("next_page_token"):
        raise ValueError("IEX bars incomplete")
    out=[]
    seen=set()
    for r in payload["bars"]:
        d=str(r.get("t") or "")[:10]
        if d>expected:
            continue
        try:
            v={k:float(r[field]) for k,field in
               [("open","o"),("high","h"),("low","l"),("close","c"),
                ("volume","v")]}
        except (ValueError,TypeError,KeyError):
            raise ValueError("Invalid IEX bar") from None
        if not (len(d)==10 and d not in seen and all(math.isfinite(x) for x in v.values())
                and min(v.values())>0 and v["high"]>=max(v["open"],v["close"],v["low"])
                and v["low"]<=min(v["open"],v["close"])):
            raise ValueError("Invalid or duplicate IEX bar")
        seen.add(d)
        out.append({"date":d,**v})
    return sorted(out,key=lambda x:x["date"])


def _rsi14(bars):
    changes=[bars[i]["close"]-bars[i-1]["close"] for i in range(1,len(bars))]
    ups=[max(c,0) for c in changes]
    downs=[max(-c,0) for c in changes]
    up=mean(ups[:14]);down=mean(downs[:14])
    for u,d in zip(ups[14:],downs[14:]):
        up=(13*up+u)/14
        down=(13*down+d)/14
    return 100-(100/(1+up/down)) if down else (100 if up else 50)


def _atr14_before_signal(bars):
    prior=bars[:-1]
    tr=[max(b["high"]-b["low"],abs(b["high"]-a["close"]),abs(b["low"]-a["close"]))
        for a,b in zip(prior,prior[1:])]
    atr=mean(tr[:14])
    for t in tr[14:]:
        atr=(13*atr+t)/14
    return atr


def summarize(bars, calendar, feed):
    """Pure date-aligned math; never scores an unverified clinical program."""
    last_sessions=calendar["recentSessions"]
    if len(bars)<61 or [b["date"] for b in bars[-61:]]!=last_sessions:
        raise ValueError("Missing complete recent exchange sessions")
    current=bars[-1]
    prior=bars[:-1]
    atr=_atr14_before_signal(bars)
    if atr<=0:
        raise ValueError("ATR unavailable")
    sma20=mean(b["close"] for b in bars[-20:])
    sma50=mean(b["close"] for b in bars[-50:])
    rvol=current["volume"]/mean(b["volume"] for b in prior[-20:])
    base=prior[-10:]
    base_high=max(b["high"] for b in base)
    base_low=min(b["low"] for b in base)
    risk_stop=base_low-.25*atr
    risk=(current["close"]-risk_stop)/current["close"]*100 if risk_stop>0 else None
    trend=current["close"]>=sma20>=sma50
    base_tight=(base_high-base_low)<=3*atr
    stabilizing=min(b["low"] for b in base[-5:])>=min(b["low"] for b in base[:5])
    breakout=current["close"]>base_high+.1*atr
    if breakout and rvol>=1.5 and trend and risk is not None and 0<risk<=8:
        label="BREAKOUT_REVIEW"
    elif base_tight and stabilizing and current["close"]>=sma20:
        label="BASE_FORMING"
    elif current["close"]<sma20:
        label="BELOW_SMA20"
    elif risk is not None and risk>8:
        label="ENTRY_RISK_OVER_8_PERCENT"
    else:
        label="WATCH"
    return {
        "status":"OK","technicalScreen":label,
        "provider":"ALPACA","feed":feed.upper(),
        "feedCoverage":"SIP_CONSOLIDATED" if feed=="sip" else "IEX_SINGLE_EXCHANGE",
        "adjustment":"split","date":current["date"],
        "close":round(current["close"],4),
        "sma20":round(sma20,4),"sma50":round(sma50,4),
        "atr14":round(atr,4),"rsi14":round(_rsi14(bars),1),
        "rvol20":round(rvol,2),
        "baseLow":round(base_low,4),"baseHigh":round(base_high,4),
        "stopReference":round(risk_stop,4) if risk_stop>0 else None,
        "riskToStopPct":round(risk,2) if risk is not None else None,
        "change20Pct":round((current["close"]/prior[-20]["close"]-1)*100,2),
        "trendAboveSma20Sma50":trend,"baseTight":base_tight,
        "stabilizingLows":stabilizing,"breakout":breakout,
        "volumeConfirmed":rvol>=1.5 if feed=="sip" else None,
        "riskResearchOnly":True,"programEligibilityVerified":False,
        "noPositionOrTradingAccess":True,
        "message":("Ticker-level market research only. A ticker may have multiple distinct "
                   "clinical programs. Trial-specific evidence and FDA dates are separate. "
                   "The conditions are not historically validated.")
    }


def for_ticker(ticker, feed="sip", *, now=None):
    ticker=str(ticker or "").strip().upper()
    if not SYMBOL.fullmatch(ticker) or feed not in VALID_FEEDS:
        return {"ticker":ticker,"status":"UNAVAILABLE","reason":"INVALID_TICKER_OR_FEED",
                "provider":"ALPACA"}
    now=now or datetime.now(timezone.utc)
    try:
        calendar=session_context(now)
        key=(ticker,feed,calendar["expectedSession"])
        with _LOCK:
            old=_CACHE.get(key)
            if old and time.monotonic()-old[0]<600:
                return dict(old[1])
        bars=_get_daily(ticker,feed,now,calendar)
        metrics=summarize(bars,calendar,feed)
        metrics["ticker"]=ticker
        with _LOCK:
            _CACHE[key]=(time.monotonic(),dict(metrics))
            if len(_CACHE)>150:
                earliest=min(_CACHE,key=lambda k:_CACHE[k][0])
                _CACHE.pop(earliest,None)
        return metrics
    except (ValueError,KeyError,TypeError,OSError,OverflowError,ImportError):
        return {"ticker":ticker,"provider":"ALPACA","feed":feed.upper(),
                "status":"UNAVAILABLE","reason":"SOURCE_OR_MARKET_SESSION_UNVERIFIED",
                "noPositionOrTradingAccess":True}
