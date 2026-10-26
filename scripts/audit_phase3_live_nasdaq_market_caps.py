#!/usr/bin/env python3
"""Bounded, read-only current Nasdaq market-cap recheck for the 130 census issuers.

A failed lookup is UNRESOLVED, never replaced by a historical snapshot.
No trading, Pipeline promotion, saved market-cap mutation or scan scheduling.
"""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
CAPS = ROOT / "data/phase_pipeline_market_caps.csv"
LOW, HIGH = 300_000_000, 10_000_000_000
MAX_BYTES = 250_000


def parse_market_cap(payload):
    """Only the original Nasdaq summary field is acceptable."""
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        raise ValueError("Invalid Nasdaq summary envelope")
    data = payload["data"]
    if data.get("assetClass") not in (None, "STOCKS", "stocks"):
        raise ValueError("Unexpected Nasdaq asset class")
    value = data.get("summaryData", {}).get("MarketCap", {}).get("value")
    if not isinstance(value, str):
        raise ValueError("No original Nasdaq market-cap value")
    clean = value.strip().replace(",", "").replace("$", "")
    if not re.fullmatch(r"\d+(?:\.\d+)?", clean):
        raise ValueError("Non-numeric original Nasdaq market cap")
    number = float(clean)
    if not 0 < number < 1e15:
        raise ValueError("Implausible original Nasdaq market cap")
    return number


def fetch(ticker):
    url = f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PDUFAReadOnlyResearch/1.0)",
        "Accept": "application/json", "Referer": "https://www.nasdaq.com/",
    })
    with urllib.request.urlopen(request, timeout=9) as response:
        if response.status != 200:
            raise ValueError("Nasdaq HTTP response not 200")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Nasdaq response exceeds bounded size")
    return parse_market_cap(json.loads(data)), url


def audit(fetcher=fetch):
    trials = list(csv.DictReader(TRIALS.open(encoding="utf-8-sig", newline="")))
    caps = list(csv.DictReader(CAPS.open(encoding="utf-8-sig", newline="")))
    tickers = sorted({r["ticker"] for r in trials})
    if len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741 or len(tickers) != 130:
        raise ValueError("Original 741-trial/130-issuer census mismatch")
    by_ticker = {r["ticker"]: r for r in caps}
    if len(by_ticker) != len(caps) or not set(tickers).issubset(by_ticker):
        raise ValueError("Original cap snapshots missing or duplicated")
    rows = []
    for index, ticker in enumerate(tickers):
        if index:
            time.sleep(0.25)
        saved = by_ticker[ticker]
        record = {"ticker": ticker, "original_snapshot_usd": saved["market_cap"],
                  "original_snapshot_checked_at": saved["market_cap_checked_at"],
                  "fresh_cap_usd": None, "fresh_checked_at_utc": None,
                  "source_url": f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks",
                  "classification": "UNRESOLVED", "failure": None,
                  "qualified_pipeline": None}
        try:
            cap, url = fetcher(ticker)
            if url != record["source_url"] or not isinstance(cap, (int, float)) or not 0 < cap < 1e15:
                raise ValueError("Source URL or current market cap invalid")
            record["fresh_cap_usd"] = cap
            record["fresh_checked_at_utc"] = datetime.now(timezone.utc).isoformat()
            record["classification"] = "IN_RANGE" if LOW <= cap <= HIGH else ("BELOW_300M" if cap < LOW else "ABOVE_10B")
        except (urllib.error.URLError, OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            record["failure"] = type(exc).__name__ + ": " + str(exc)[:160]
        rows.append(record)
    counts = {k: sum(r["classification"] == k for r in rows) for k in ("IN_RANGE", "BELOW_300M", "ABOVE_10B", "UNRESOLVED")}
    return {"scope": "LIVE_ORIGINAL_NASDAQ_CAP_RESEARCH_ONLY",
            "checked_at_utc": datetime.now(timezone.utc).isoformat(),
            "issuer_count": 130, "counts": counts, "fresh_verified": 130 - counts["UNRESOLVED"],
            "qualified_pipeline_count": None, "issuers": rows,
            "limitations": "HTTP retrieval time is not Nasdaq quote publication time; a returned market cap can be delayed. No FDA, ownership, active program or Pipeline qualification."}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_live_nasdaq_market_caps.py output.json")
    result = audit()
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Original issuer cap rechecks:", result["issuer_count"], "/130")
    print("Successfully fetched:", result["fresh_verified"], "/130")
    print("Cap classifications:", result["counts"])
    print("Qualified Pipeline: UNKNOWN; no source failures promoted.")
