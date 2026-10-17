"""Small read-only program-specific WT technical lookup.

WT can include any published Pipeline exact trial, not only the 19 GEM records.
The GEM factor engine is reused; identical stock EOD data may be shared by
several trial IDs, but clinical/financing eligibility is NEVER copied between
programs based on ticker.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import math
import re
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import logging
import threading
import time

from .source_workspace import as_rows, fetch, unique, workspace
from .gem_research_adapter import analyze_member, parse_runway

LOG = logging.getLogger(__name__)
_CONTEXT_LOCK = threading.Lock()
_CONTEXT: dict = {"at": 0.0, "data": None}
_NAMES = (
    "step7_market_status.csv",
    "pdufa_candidates.csv",
    "fda_review_engine.csv",
    "prediction_engine_history.csv",
    "second_financing_status.csv",
    "gem_two_close_recheck.csv",
    "gem_runway_evidence.json",
)


def _fetch_one(name: str) -> tuple[str, str, str]:
    try:
        return name, fetch(name), ""
    except (OSError, ValueError, UnicodeError) as exc:
        return name, "", type(exc).__name__


def _context() -> dict:
    with _CONTEXT_LOCK:
        if _CONTEXT["data"] is not None and time.monotonic() - _CONTEXT["at"] < 300:
            return _CONTEXT["data"]
        with ThreadPoolExecutor(max_workers=7) as executor:
            files = list(executor.map(_fetch_one, _NAMES))
        data, missing = {}, []
        for name, value, issue in files:
            data[name] = value
            if issue:
                missing.append(name + ": " + issue)
        rows = {name: as_rows(data[name]) for name in _NAMES if name.endswith(".csv")}
        events = unique(rows["pdufa_candidates.csv"], "event_key")
        for name in ("fda_review_engine.csv", "prediction_engine_history.csv"):
            for key, row in unique(rows[name], "event_key").items():
                events.setdefault(key, row)
        result = {
            "market": unique(rows["step7_market_status.csv"], "ticker"),
            "events": events,
            "financing": unique(rows["second_financing_status.csv"], "event_key"),
            "recheck": unique(rows["gem_two_close_recheck.csv"], "event_key"),
            "runway": parse_runway(data["gem_runway_evidence.json"]),
            "missingSources": missing,
        }
        _CONTEXT.update(at=time.monotonic(), data=result)
        return result


# A read-only, per-WT-trial on-demand market source; not a nightly scanner.
_EOD_CACHE: dict[str, tuple[float, dict | None]] = {}
_EOD_LOCK = threading.Lock()
_VALID_TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")


def _interpret_yahoo(payload: dict, ticker: str, url: str, today) -> dict | None:
    """Validate Yahoo daily bars strictly before passing to the GEM EOD model."""
    results = payload.get("chart", {}).get("result") or []
    if len(results) != 1:
        return None
    entry = results[0]
    meta = entry.get("meta") or {}
    if (str(meta.get("symbol") or "").upper() != ticker
            or str(meta.get("currency") or "").upper() != "USD"
            or str(meta.get("instrumentType") or "").upper() != "EQUITY"):
        return None
    raw = (entry.get("indicators") or {}).get("quote") or []
    timestamps = entry.get("timestamp") or []
    if len(raw) != 1 or not isinstance(timestamps, list):
        return None
    closes = raw[0].get("close") or []
    volumes = raw[0].get("volume") or []
    if not (len(closes) == len(volumes) == len(timestamps)):
        return None
    # US market session dates from Eastern Time: never use current intraday
    # quotes for a completed daily bar, and never accept duplicate sessions.
    seen = set()
    bars = []
    now_eastern = datetime.now(ZoneInfo("America/New_York"))
    for timestamp, close, volume in zip(timestamps, closes, volumes):
        try:
            day = datetime.fromtimestamp(int(timestamp), timezone.utc).astimezone(
                ZoneInfo("America/New_York")
            ).date()
            value = float(close)
            shares = float(volume)
            if (day > today or day in seen or not math.isfinite(value)
                    or value <= 0 or not math.isfinite(shares) or shares < 0
                    or (day == now_eastern.date() and now_eastern.hour < 17)):
                # Do not count an unclosed US trading session as a daily close.
                continue
        except (ValueError, OverflowError, TypeError):
            continue
        seen.add(day)
        bars.append({"date": day.isoformat(), "close": value, "volume": shares})
    bars.sort(key=lambda v: v["date"])
    if len(bars) < 21:
        return None
    bars = bars[-120:]
    from .legacy_gem_trading_advisory import _days_since_session
    last_day = datetime.fromisoformat(bars[-1]["date"]).date()
    if _days_since_session(last_day, today) is None:
        return None
    # A lagging feed is retained but will be marked stale by GEM's own model.
    volume_base = sum(b["volume"] for b in bars[-21:-1]) / 20
    return {
        "ticker": ticker,
        "market_status": "MARKET_UPDATED",
        "last_session": last_day.isoformat(),
        "last_close_usd": bars[-1]["close"],
        "last_volume": bars[-1]["volume"],
        "relative_volume": bars[-1]["volume"] / volume_base if volume_base > 0 else None,
        "price_bars_json": json.dumps(bars, separators=(",", ":")),
        "market_source": url,
        "market_origin": "WT_ON_DEMAND_YAHOO_VERIFIED_EOD",
    }


def _download_eod(ticker: str, today) -> dict | None:
    if not _VALID_TICKER.fullmatch(ticker):
        return None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = "https://" + host + "/v8/finance/chart/" + quote(ticker, safe="") + "?range=6mo&interval=1d&events=history"
        try:
            request = Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; PDUFA-trial-EOD-research/1.0)",
                "Accept": "application/json",
            })
            with urlopen(request, timeout=6) as response:
                blob = response.read(750_001)
                if len(blob) > 750_000:
                    continue
            parsed = _interpret_yahoo(json.loads(blob), ticker, url, today)
            if parsed:
                return parsed
        except (OSError, ValueError, TypeError, UnicodeError, KeyError):
            continue
    return None


def _market_for_ticker(ticker: str, published: dict, today) -> dict:
    """Prefer source-verified existing GEM data; refresh absent/stale bars for WT."""
    from .legacy_gem_trading_advisory import _bars, _safe_date, _days_since_session
    old = published.get(ticker)
    if old and old.get("market_status") == "MARKET_UPDATED":
        day = _safe_date(old.get("last_session"))
        if (day and _days_since_session(day, today) is not None
                and _days_since_session(day, today) <= 2 and len(_bars(old, today)) >= 60):
            return published
    with _EOD_LOCK:
        cached = _EOD_CACHE.get(ticker)
        if cached is not None and time.monotonic() - cached[0] < 900:
            recent = cached[1]
        else:
            recent = _download_eod(ticker, today)
            _EOD_CACHE[ticker] = (time.monotonic(), recent)
    if recent is None:
        return published
    return {**published, ticker: recent}


# Exact replication of app.py's eight ENTRY / EXIT watchlist columns.
# Original ticker-level scanner output may legitimately be absent.
_SIGNAL_ROWS: dict = {"at": 0.0, "by_key": {}}
_SIGNAL_LOCK = threading.Lock()
_SIGNAL_NAMES = (
    "Volume / RVOL", "Bollinger (20,2)", "Phase 3 AVWAP",
    "EMA (10/20/50)", "RSI (14)", "MACD (12/26/9)", "OBV", "ATR (14)"
)


def _signals_for_ticker(ticker: str) -> dict:
    with _SIGNAL_LOCK:
        if time.monotonic() - _SIGNAL_ROWS["at"] > 300:
            index = {}
            try:
                raw = fetch("watchlist_indicator_signals.csv")
                for record in as_rows(raw):
                    symbol = str(record.get("ticker") or "").strip().upper()
                    mode = str(record.get("mode") or "").strip().upper()
                    if _VALID_TICKER.fullmatch(symbol) and mode in {"ENTRY", "EXIT"}:
                        index[(symbol, mode)] = record
            except Exception as exc:
                # Optional scanner data must never block verified trial scoring.
                LOG.warning(
                    "STREAMLIT_WATCHLIST_SIGNAL_OPTIONAL status=NOT_SCANNED error_type=%s",
                    type(exc).__name__,
                )
            _SIGNAL_ROWS.update(at=time.monotonic(), by_key=index)
        result = {}
        for mode in ("ENTRY", "EXIT"):
            record = _SIGNAL_ROWS["by_key"].get((ticker, mode), {})
            result[mode] = {
                "signals": {
                    name: str(record.get(name) or "").strip() or "NOT SCANNED"
                    for name in _SIGNAL_NAMES
                },
                "updated": str(record.get("updated_at") or "").strip() or "NOT SCANNED",
            }
        return result


def for_exact_program(exact_key: str) -> dict:
    if not exact_key.startswith(("APPLICATION|", "TRIAL|")):
        raise ValueError("Invalid exact program")
    snapshot = workspace()
    for stage in ("GEM", "GEM_JR"):
        for row in snapshot.get("members", {}).get(stage, {}).get("rows", []):
            if row.get("id") == exact_key and "technical" in row:
                # Return GEM's actual existing score, not a separate WT formula.
                return {
                    "source": "SAME_GEM_JR_GEM_PROFILE",
                    "watchlistSignals": _signals_for_ticker(row["ticker"]),
                    "stage": stage,
                    "technical": row["technical"],
                    "asOf": snapshot.get("asOf"),
                    "scope": "Exact program; market bars represent ticker-level observations.",
                }
    row = next((r for r in snapshot.get("pipeline", []) if r.get("id") == exact_key), None)
    if row is None:
        return {
            "source": "PUBLISHED_PROGRAM_NOT_CURRENT",
            "watchlistSignals": {"ENTRY": {"signals": {}, "updated": "NOT SCANNED"}, "EXIT": {"signals": {}, "updated": "NOT SCANNED"}},
            "technical": None, "asOf": snapshot.get("asOf"),
            "scope": "Historical program identity retained. No current trial evidence.",
        }
    context = _context()
    event_key = row.get("eventKey") or ""
    event = context["events"].get(event_key, {}) if exact_key.startswith("APPLICATION|") else {}
    # A trial with the same ticker NEVER inherits an application-level event,
    # positive endpoint, second financing, or regulatory certainty.
    from datetime import date
    from zoneinfo import ZoneInfo
    from datetime import datetime
    today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    analysis_row = dict(row)
    if exact_key.startswith("TRIAL|"):
        analysis_row["nctId"] = exact_key.split("|", 1)[1]
    market_rows = _market_for_ticker(row["ticker"], context["market"], today)
    try:
        technical = analyze_member(
            analysis_row, event,
            context["financing"].get(event_key, {}) if event else {},
            context["recheck"].get(event_key, {}) if event else {},
            market_rows, context["runway"].get(row["ticker"]),
            (snapshot.get("sourceHealth") or {}).get("publishedScan") or {},
            today,
        )
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        LOG.warning("WT exact research unavailable: %s", type(exc).__name__)
        return {
            "source": "WT_MARKET_RESEARCH_UNAVAILABLE",
            "watchlistSignals": _signals_for_ticker(row["ticker"]),
            "technical": None,
            "asOf": snapshot.get("asOf"),
            "missingSources": context["missingSources"],
        }
    return {
        "source": "ORIGINAL_GEM_INDICATOR_MODEL_ON_EXACT_PIPELINE_TRIAL",
        "watchlistSignals": _signals_for_ticker(row["ticker"]),
        "technical": technical,
        "asOf": snapshot.get("asOf"),
        "missingSources": context["missingSources"],
        "marketOrigin": (market_rows.get(row["ticker"]) or {}).get("market_origin", "PUBLISHED_GEM_EOD_FEED"),
        "scope": ("Market indicators are ticker-level and may be shared; Phase 3 "
                  "and financing gates remain exact-program only; no orders authorized."),
    }
