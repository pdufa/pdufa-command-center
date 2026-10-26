#!/usr/bin/env python3
"""Read-only live Nasdaq cap check for 130 historical census tickers.

A retrieval timestamp is NOT a quote's as-of time. Quote response freshness
is unknown unless the upstream data explicitly provides a parseable as-of.
No issuer/program/FDA/PDUFA/Pipeline qualification is inferred.
"""
import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
LOW, HIGH = 300_000_000, 10_000_000_000
MAX_BYTES = 300_000


def parse_cap(value):
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        cap = float(value)
    elif isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "")
        if cleaned in ("", "N/A", "--"):
            return None
        scale = 1
        if cleaned[-1:].upper() in ("K", "M", "B", "T"):
            scale = {"K":1e3,"M":1e6,"B":1e9,"T":1e12}[cleaned[-1:].upper()]
            cleaned = cleaned[:-1]
        try:
            cap = float(cleaned) * scale
        except ValueError:
            return None
    else:
        return None
    return cap if math.isfinite(cap) and cap > 0 else None


def read_ticker(ticker):
    url = f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; PDUFAResearch/1.0)",
        "Origin": "https://www.nasdaq.com",
        "Referer": "https://www.nasdaq.com/",
    })
    result = {"ticker":ticker,"source_url":url,"retrieved_at_utc":datetime.now(timezone.utc).isoformat(),
              "market_cap_usd":None,"classification":"SOURCE_UNVERIFIED",
              "source_quote_as_of":None,"live_quote_freshness_verified":False,
              "qualified_pipeline":None}
    try:
        with urllib.request.urlopen(request,timeout=12) as response:
            if response.status != 200 or response.geturl() != url:
                raise ValueError("Unexpected response or redirect")
            raw = response.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Oversized source")
        payload = json.loads(raw)
        if not isinstance(payload,dict) or not isinstance(payload.get("data"),dict):
            raise ValueError("Invalid Nasdaq payload")
        data = payload["data"]
        summary = data.get("summaryData")
        if not isinstance(summary,dict):
            raise ValueError("Missing Nasdaq summaryData")
        cap = parse_cap(summary.get("MarketCap"))
        if cap is None:
            raise ValueError("Missing/unparseable market cap")
        result["market_cap_usd"] = cap
        result["classification"] = ("SOURCE_RETRIEVED_BELOW_300M" if cap < LOW else
                                    "SOURCE_RETRIEVED_ABOVE_10B" if cap > HIGH else
                                    "SOURCE_RETRIEVED_IN_RANGE_ASOF_UNKNOWN")
        # Nasdaq summary endpoint may omit a reliable per-value as-of date.
        # Never turn HTTP fetch time into market data freshness.
    except Exception as error:
        result["error_type"] = type(error).__name__[:80]
    return result


def run(output):
    trials=list(csv.DictReader((ROOT/"data/phase3_all_years_300m_10b_trials.csv").open(encoding="utf-8-sig")))
    tickers=sorted({r["ticker"] for r in trials})
    if len(trials)!=741 or len({r["nct_id"] for r in trials})!=741 or len(tickers)!=130 or any(not re.fullmatch(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?",t) for t in tickers):
        raise ValueError("Original 741/130 census not reconciled")
    with ThreadPoolExecutor(max_workers=3) as pool:
        records=list(pool.map(read_ticker,tickers))
    if len(records)!=130 or [r["ticker"] for r in records]!=tickers:
        raise ValueError("Original ticker results incomplete")
    counts={k:sum(x["classification"]==k for x in records) for k in
            ("SOURCE_RETRIEVED_BELOW_300M","SOURCE_RETRIEVED_ABOVE_10B",
             "SOURCE_RETRIEVED_IN_RANGE_ASOF_UNKNOWN","SOURCE_UNVERIFIED")}
    report={"type":"NASDAQ_PUBLIC_QUOTE_RETRIEVAL_RESEARCH_ONLY",
            "checked_at_utc":datetime.now(timezone.utc).isoformat(),
            "original_issuer_denominator":130,"original_trial_denominator":741,
            "retrieved_cap_count":130-counts["SOURCE_UNVERIFIED"],
            "classifications":counts,
            "quote_asof_verified_count":0,"qualified_pipeline_count":None,
            "issuer_records":records,
            "limits":"Nasdaq public summaryData MarketCap retrieval. Retrieval time is not quote time; values may be delayed/stale. No current-cap gate promotion, rights or FDA verification."}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("Public Nasdaq market-cap source values retrieved:",report["retrieved_cap_count"],"/130")
    print("Source classifications:",counts)
    print("Source market-cap as-of freshness verified: 0/130. Qualified Pipeline UNKNOWN.")
    return 0


if __name__=="__main__":
    if len(sys.argv)!=2:
        sys.exit("Usage: check_phase3_nasdaq_current_130.py <output.json>")
    sys.exit(run(Path(sys.argv[1])))
