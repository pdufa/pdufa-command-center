"""Bounded daily end-of-day quotes for exact Step 7 financing-event tickers.

Market readings are provider-supplied and delayed, not exchange-certified.
Nothing in this file makes a stock ENTRY READY.
"""
from __future__ import annotations
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.recheck_events import market_check
DATA = ROOT / "data"
OUTPUT = DATA / "step7_market_status.csv"
STATE = DATA / "step7_market_status.json"

FIELDS = (
    "ticker", "checked_at_utc", "market_status", "last_session",
    "last_close_usd", "last_volume", "prior20_avg_volume", "relative_volume",
    "trailing_momentum_pct", "sessions_available", "market_source",
    "last_session_freshness", "note", "price_bars_json",
)

def load_tickers():
    path = DATA / "second_financing_status.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return sorted({r.get("event_key", "").split("|", 1)[0].strip().upper()
                   for r in rows
                   if re.fullmatch(r"[A-Z0-9.-]{1,12}", r.get("event_key", "").split("|", 1)[0].strip().upper())})

def safe_val(value):
    return "" if value is None else str(value)

def market_freshness(session, today):
    """Calendar-day bound includes one weekend and one Monday holiday buffer."""
    try:
        d = date.fromisoformat(str(session))
    except ValueError:
        return "NO VALID PRICE SESSION"
    age = (today - d).days
    return "FUTURE PRICE" if age < 0 else "RECENT EOD" if age <= 5 else "STALE EOD"

def collect(tickers, provider=market_check, now=None, pace=0.2):
    now = now or datetime.now(timezone.utc)
    today = now.date()
    entries = []
    for idx, ticker in enumerate(tickers):
        try:
            result = provider(ticker)
        except Exception as err:
            result = {"status":"SOURCE_UNAVAILABLE","note":f"Provider error: {type(err).__name__}"}
        session = safe_val(result.get("last_session"))
        marker = market_freshness(session, today)
        entries.append({
            "ticker": ticker,
            "checked_at_utc": now.isoformat(),
            "market_status": result.get("status", "SOURCE_UNAVAILABLE"),
            "last_session": session,
            "last_close_usd": safe_val(result.get("price")),
            "last_volume": safe_val(result.get("last_volume")),
            "prior20_avg_volume": safe_val(result.get("prior20_volume")),
            "relative_volume": safe_val(result.get("relative_volume")),
            "trailing_momentum_pct": safe_val(result.get("return30")),
            "sessions_available": safe_val(result.get("sessions_available")),
            "market_source": result.get("source", ""),
            "last_session_freshness": marker,
            "note": result.get("note", ""),
            "price_bars_json": json.dumps(result.get("price_bars", []), separators=(",",":")),
        })
        if idx < len(tickers)-1 and pace>0:
            time.sleep(pace)
    return entries

def main():
    tickers = load_tickers()
    rows = collect(tickers)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    good=sum(r["market_status"]=="MARKET_UPDATED" and r["last_session_freshness"]=="RECENT EOD"
             for r in rows)
    status={
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "ticker_scope":"Unique tickers from saved exact-event financing reviews",
        "expected":len(tickers), "fresh_eod":good,
        "unavailable_or_stale":len(rows)-good,
        "status":"COMPLETE" if good==len(rows) and good else "PARTIAL",
        "note":"Quotes are delayed/provider-reported. Price issuer mapping, corporate actions, "
               "post-readout stabilization and independently verified volume normalization remain review.",
    }
    STATE.write_text(json.dumps(status, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(status))
    return 0 if rows else 1

if __name__ == "__main__":
    raise SystemExit(main())
