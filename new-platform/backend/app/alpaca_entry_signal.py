"""Read-only, exact-program entry rules v1. Thresholds are not backtested.

Consolidated split-adjusted history supplies all historical price/volume checks.
An EOD setup becomes green BUY only during the next exchange session, with a
fresh executable ask in the entry band. No order endpoint is ever called.
"""
from __future__ import annotations

import json
import math
import threading
import time
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .alpaca_market_chart import ALPACA_HOST, SYMBOL, TZ, _credentials, _feed

_CACHE = {}
_LOCK = threading.Lock()
MODEL = "BASE_BREAKOUT_V1_UNVALIDATED"


def _number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean market value")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite market value")
    return result


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _request(path, params):
    credentials = _credentials()
    if credentials is None:
        raise ValueError("Alpaca market-data credentials are not configured")
    request = Request(ALPACA_HOST + path + "?" + urlencode(params), headers={
        "APCA-API-KEY-ID": credentials[0], "APCA-API-SECRET-KEY": credentials[1],
        "Accept": "application/json", "User-Agent": "PDUFA-Entry-Rules/1.0",
    })
    with urlopen(request, timeout=9) as response:
        raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise ValueError("Market-data response is too large")
    return json.loads(raw)


def session_context(now):
    """Real XNYS holidays/early closes; wait 20 minutes for EOD availability."""
    import exchange_calendars as xcals
    import pandas as pd
    calendar = xcals.get_calendar("XNYS")
    sessions = calendar.sessions_in_range(
        pd.Timestamp((now - timedelta(days=180)).date()),
        pd.Timestamp((now + timedelta(days=14)).date()),
    )
    completed = [s for s in sessions
                 if calendar.session_close(s).to_pydatetime() + timedelta(minutes=20) <= now]
    if not completed:
        raise ValueError("Exchange calendar is unavailable")
    last = completed[-1]
    next_day = calendar.next_session(last)
    return {
        "expectedSession": last.date().isoformat(),
        "recentSessions": [s.date().isoformat() for s in completed[-61:]],
        "entrySession": next_day.date().isoformat(),
        "entryOpen": calendar.session_open(next_day).to_pydatetime(),
        "entryClose": calendar.session_close(next_day).to_pydatetime(),
    }


def history(ticker, anchor, expected_session, now):
    """Free delayed historical SIP; never mix IEX volume into these checks."""
    start = min(now.date() - timedelta(days=180), anchor - timedelta(days=10))
    cache_key = (ticker, start.isoformat(), expected_session)
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached and time.monotonic() - cached[0] < 300:
            return cached[1]
    result = _request("/v2/stocks/" + quote(ticker, safe="") + "/bars", {
        "timeframe": "1Day", "start": start.isoformat(),
        "end": (now - timedelta(minutes=16)).isoformat(),
        "limit": 10000, "adjustment": "split", "feed": "sip", "sort": "asc",
    })
    if result.get("next_page_token") or not isinstance(result.get("bars"), list):
        raise ValueError("Consolidated history is incomplete")
    bars, seen = [], set()
    for raw in result["bars"]:
        day = _day(raw.get("t"))
        if day is None:
            raise ValueError("History contains an invalid session date")
        if day.isoformat() > expected_session:
            continue  # Forming session is NEVER used as a completed daily bar.
        o, h, l, c, v, vw = (_number(raw.get(k)) for k in ("o", "h", "l", "c", "v", "vw"))
        if (day in seen or min(o, h, l, c, vw) <= 0 or v <= 0
                or h < max(o, l, c) or l > min(o, h, c)):
            raise ValueError("History contains duplicate or invalid market bars")
        seen.add(day)
        bars.append(dict(date=day.isoformat(), open=o, high=h, low=l,
                         close=c, volume=v, vwap=vw))
    bars.sort(key=lambda b: b["date"])
    with _LOCK:
        _CACHE[cache_key] = (time.monotonic(), bars)
        if len(_CACHE) > 200:
            oldest = min(_CACHE, key=lambda k: _CACHE[k][0])
            _CACHE.pop(oldest, None)
    return bars


def live_quote(ticker, now):
    feed = _feed()
    result = _request("/v2/stocks/" + quote(ticker, safe="") + "/quotes/latest", {"feed": feed})
    raw = result.get("quote") or {}
    timestamp = datetime.fromisoformat(str(raw.get("t", "")).replace("Z", "+00:00"))
    bid, ask = _number(raw.get("bp")), _number(raw.get("ap"))
    if timestamp.tzinfo is None or not 0 <= (now - timestamp).total_seconds() <= 60:
        raise ValueError("Live quote is stale")
    if bid <= 0 or ask < bid:
        raise ValueError("Live quote has an invalid bid/ask")
    return {"bid": bid, "ask": ask, "asOf": timestamp.isoformat(), "feed": feed.upper()}


def calculate(bars, *, anchor, calendar):
    """Pure EOD arithmetic. Every base/ATR/average excludes the signal day."""
    if len(bars) < 61:
        raise ValueError("Need 60 preceding sessions plus the completed signal session")
    if bars[-1]["date"] != calendar["expectedSession"]:
        raise ValueError("Latest completed market session is missing")
    if [b["date"] for b in bars[-61:]] != calendar["recentSessions"]:
        raise ValueError("Recent daily history has missing or duplicate exchange sessions")
    if _day(bars[0]["date"]) >= anchor:
        raise ValueError("History does not cover the financing anchor")
    prior, signal = bars[:-1], bars[-1]
    true_ranges = [max(b["high"]-b["low"], abs(b["high"]-a["close"]),
                       abs(b["low"]-a["close"])) for a, b in zip(prior, prior[1:])]
    atr = sum(true_ranges[:14]) / 14
    for tr in true_ranges[14:]:
        atr = (atr * 13 + tr) / 14
    if atr <= 0:
        raise ValueError("ATR is unavailable")
    base = prior[-10:]
    high, low = max(b["high"] for b in base), min(b["low"] for b in base)
    recent_low = min(b["low"] for b in base[-5:])
    older_low = min(b["low"] for b in base[:5])
    average = sum(b["volume"] for b in prior[-20:]) / 20
    anchored = [b for b in bars if _day(b["date"]) >= anchor]
    if not anchored or average <= 0:
        raise ValueError("Volume/VWAP coverage is incomplete")
    avwap = sum(b["vwap"] * b["volume"] for b in anchored) / sum(b["volume"] for b in anchored)
    # Price bands are executable cents for >=$1 stocks; sub-dollar uses 4 dp.
    scale = 100 if high >= 1 else 10000
    trigger = math.ceil((high + .1 * atr) * scale - 1e-8) / scale
    maximum = math.floor((trigger + .5 * atr) * scale + 1e-8) / scale
    stop = math.floor((low - .25 * atr) * scale + 1e-8) / scale
    if stop <= 0 or maximum <= trigger:
        raise ValueError("No usable entry/stop price band")
    checks = [
        {"label": "Tight 10-session base", "pass": high-low <= 3*atr,
         "actual": high-low, "target": 3*atr, "rule": "Base range ≤ 3 × prior-session ATR14"},
        {"label": "Stabilizing lows", "pass": recent_low >= older_low,
         "actual": recent_low, "target": older_low, "rule": "Latest 5-session low ≥ preceding 5-session low"},
        {"label": "Closing breakout", "pass": signal["close"] > trigger,
         "actual": signal["close"], "target": trigger, "rule": "Completed close > base high + 0.1 × ATR"},
        {"label": "Consolidated volume", "pass": signal["volume"] >= 1.5*average,
         "actual": signal["volume"]/average, "target": 1.5, "rule": "Session volume / preceding 20-session average ≥ 1.5"},
        {"label": "Financing-anchored VWAP", "pass": signal["close"] > avwap,
         "actual": signal["close"], "target": avwap, "rule": "Close > financing-date bar-based AVWAP"},
    ]
    return {"checks": checks, "setupConfirmed": all(c["pass"] for c in checks),
            "entryTrigger": trigger, "maximumEntry": maximum, "initialStop": stop,
            "atr14": atr, "baseHigh": high, "baseLow": low, "rvol20": signal["volume"]/average,
            "anchoredVwap": avwap, "anchorDate": anchor.isoformat(),
            "signalSession": signal["date"], "signalClose": signal["close"]}


def entry_for_program(exact_key, ticker, *, now=None):
    from .source_workspace import workspace
    from .wt_research import _context
    from .gem_research_adapter import verify_benchmarks, RESOLVED
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(TZ).date()
    result = {"provider": "ALPACA", "ticker": ticker, "model": MODEL,
              "status": "UNAVAILABLE", "green": False, "checks": [],
              "historyFeed": "SIP", "adjustment": "split",
              "calculatedAt": now.isoformat(), "orderExecutionEnabled": False,
              "disclaimer": "Initial entry rules; not backtested. Green means conditions passed, not guaranteed profit."}
    try:
        if not SYMBOL.fullmatch(ticker):
            raise ValueError("Ticker is not valid")
        snapshot = workspace()
        rows = [r for group in snapshot.get("members", {}).values() for r in group.get("rows", [])
                if r.get("id") == exact_key and r.get("ticker") == ticker]
        if not rows:
            raise ValueError("Exact program is not a current GEM/GEM JR member")
        row = rows[0]
        context = _context()
        event_key = row.get("eventKey") or ""
        event = context["events"].get(event_key, {}) if exact_key.startswith("APPLICATION|") else {}
        benchmarks = verify_benchmarks(row, event, context["financing"].get(event_key, {}),
                                       context["recheck"].get(event_key, {}), today)
        result["checks"] = [
            {"label": "Verified positive Phase 3", "pass": benchmarks["phase3"], "rule": "Exact program and source-verified successful readout"},
            {"label": "Second financing closed", "pass": benchmarks["secondFinancing"], "rule": "Two distinct verified funded closes after readout"},
        ]
        if not benchmarks["bothConfirmed"]:
            result.update(status="WAIT", message="Clinical/financing entry requirements are not verified for this exact program.")
            return result
        health = snapshot.get("sourceHealth") or {}
        scan = health.get("publishedScan") or {}
        finished = datetime.fromisoformat(str(scan.get("finishedAt") or "").replace("Z", "+00:00"))
        if (health.get("state") == "STALE" or not scan.get("complete") or context["missingSources"]
                or finished.tzinfo is None or not 0 <= (now-finished).total_seconds() <= 72*3600):
            raise ValueError("Clinical/financing source checks are incomplete or stale")
        pd_date = _day(row.get("pdufaDate"))
        if (not pd_date or not str(event.get("pdufa_confirmation") or "").startswith("VERIFIED")
                or not str(event.get("pdufa_evidence_url") or "").startswith("https://")
                or pd_date != _day(event.get("pdufa_date"))):
            raise ValueError("A source-verified PDUFA date is required")
        if (pd_date-today).days <= 14 or str(event.get("outcome") or "").upper() in RESOLVED:
            result.update(status="WAIT", message="Inside the 14-calendar-day pre-PDUFA exit window, or FDA event already resolved.")
            return result
        if str(event.get("new_dilution_flag") or "").upper() in {"YES", "TRUE", "UNRESOLVED"}:
            result.update(status="WAIT", message="New or unresolved dilution needs review before entry.")
            return result
        calendar = session_context(now)
        anchor = _day(benchmarks["secondClose"])
        bars = history(ticker, anchor, calendar["expectedSession"], now)
        calculated = calculate(bars, anchor=anchor, calendar=calendar)
        result["checks"] += calculated.pop("checks")
        result.update(calculated, entrySession=calendar["entrySession"],
                      entryOpen=calendar["entryOpen"].isoformat(), entryClose=calendar["entryClose"].isoformat())
        if not calculated["setupConfirmed"]:
            result.update(status="WAIT", message="Entry checks have not all passed. Review the failed conditions below.")
        elif now < calendar["entryOpen"]:
            result.update(status="READY_NEXT_SESSION", message="Closing setup confirmed. Wait for the next regular session and a fresh price inside the entry range.")
        elif now >= calendar["entryClose"]:
            result.update(status="UNAVAILABLE", message="Entry session closed. Waiting for a new completed-session calculation.")
        elif (pd_date-calendar["entryOpen"].date()).days <= 14:
            result.update(status="WAIT", message="Next entry session falls inside the 14-day pre-PDUFA exit window.")
        else:
            current = live_quote(ticker, now)
            result["quote"] = current
            in_band = calculated["entryTrigger"] <= current["bid"] <= current["ask"] <= calculated["maximumEntry"]
            result["checks"].append({"label": "Fresh live price in entry range", "pass": in_band,
                                     "actual": current["ask"], "target": calculated["maximumEntry"],
                                     "rule": "Bid holds trigger; ask ≤ maximum entry; quote ≤ 60 seconds old"})
            result.update(status="BUY" if in_band else "WAIT", green=in_band,
                          message="All entry conditions passed. Buy range and initial stop shown below." if in_band
                          else "Live price is outside the entry band. Wait; do not chase.")
    except (ValueError, TypeError, KeyError, OSError, ImportError, OverflowError):
        result.update(status="UNAVAILABLE", green=False,
                      message="Required source, exchange calendar, consolidated history, or fresh live quote is unavailable. No buy signal.")
    return result
