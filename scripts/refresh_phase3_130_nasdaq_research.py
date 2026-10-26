#!/usr/bin/env python3
"""Read-only original Nasdaq summary refresh for 130 historical census tickers.

An HTTP response timestamp is NOT a market-data as-of timestamp. Even a parsed
market cap is research-only until issuer, quote as-of, and corporate actions
are independently validated. Never modifies the Pipeline or historical CSV.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
BASE = "https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
MAX_BYTES = 1_000_000
LOW, HIGH = 300_000_000, 10_000_000_000

def parse_cap(value):
    """Parse a market cap only from a recognized summary field, never infer it."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(value) and value >= 0 else None
    if not isinstance(value, str):
        return None
    text = value.strip().replace(",", "").replace("$", "")
    m = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([KMBT]?)", text, re.I)
    if not m:
        return None
    result = float(m.group(1)) * {"":1, "K":1e3, "M":1e6, "B":1e9, "T":1e12}[m.group(2).upper()]
    return result if math.isfinite(result) else None

def extract_summary(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
        return None, "INVALID_SUMMARY_SHAPE"
    data = payload["data"]
    summary = data.get("summaryData")
    if not isinstance(summary, dict):
        return None, "MISSING_SUMMARY_DATA"
    field = summary.get("MarketCap")
    if not isinstance(field, dict):
        return None, "MISSING_MARKETCAP_FIELD"
    value = parse_cap(field.get("value"))
    if value is None:
        return None, "UNPARSABLE_MARKETCAP"
    return value, "SOURCE_MARKETCAP_PARSED_NO_QUOTE_ASOF"

def collect(tickers, fetch, now):
    if len(tickers) != 130 or len(set(tickers)) != 130:
        raise ValueError("Original 130 issuer scope changed")
    rows = []
    for ticker in sorted(tickers):
        if not re.fullmatch(r"[A-Z]{1,7}(?:[.-][A-Z]{1,3})?", ticker):
            raise ValueError("Invalid ticker")
        url = BASE.format(ticker=ticker)
        row = {"ticker":ticker,"source_url":url,"retrieved_at_utc":now().isoformat(),
               "market_cap_usd":None,"range_at_retrieval":"UNKNOWN",
               "quote_asof_verified":False,"issuer_identity_revalidated":False,
               "corporate_actions_checked":False,"qualified_pipeline":None}
        try:
            raw, status, content_type, final_url = fetch(url)
            if status != 200 or final_url != url or "application/json" not in content_type.lower():
                row["disposition"] = "SOURCE_HTTP_OR_CONTENT_TYPE_INVALID"
            elif len(raw) > MAX_BYTES:
                row["disposition"] = "SOURCE_TOO_LARGE"
            else:
                row["response_sha256"] = hashlib.sha256(raw).hexdigest()
                cap, disposition = extract_summary(json.loads(raw))
                row["disposition"] = disposition
                if cap is not None:
                    row["market_cap_usd"] = cap
                    row["range_at_retrieval"] = "BELOW_300M" if cap < LOW else ("ABOVE_10B" if cap > HIGH else "IN_RANGE")
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as error:
            row["disposition"] = "SOURCE_UNAVAILABLE_OR_INVALID"
            row["error_type"] = type(error).__name__
        rows.append(row)
    return {"scope":"RESEARCH_ONLY_NO_PIPELINE_PROMOTION",
            "original_census_issuers":130,
            "source_attempts":len(rows),
            "source_market_caps_parsed":sum(x["market_cap_usd"] is not None for x in rows),
            "source_errors_or_unparsed":sum(x["market_cap_usd"] is None for x in rows),
            "source_range_counts":{k:sum(x["range_at_retrieval"] == k for x in rows)
              for k in ("IN_RANGE","BELOW_300M","ABOVE_10B","UNKNOWN")},
            "independently_verified_quote_asof":0,
            "qualified_pipeline_count":None,
            "issuer_rows":rows,
            "limitations":"HTTP retrieval is not a verified market-data as-of time; corporate actions and issuer mapping require independent recheck."}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected redirect")

def live_fetch(url):
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(url, headers={"Accept":"application/json",
        "User-Agent":"Mozilla/5.0 (compatible; PDUFA-ReadOnly-Research/1.0)"})
    with opener.open(request, timeout=8) as response:
        return response.read(MAX_BYTES+1), response.status, response.headers.get("content-type",""), response.geturl()

def main(output):
    with TRIALS.open(encoding="utf-8-sig", newline="") as f:
        trials = list(csv.DictReader(f))
    if len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741:
        raise ValueError("Historical trial census changed")
    tickers = sorted({r["ticker"] for r in trials})
    report = collect(tickers, live_fetch, lambda: datetime.now(timezone.utc))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    print(f"Nasdaq original source attempts: {report['source_attempts']}/130; parsed: {report['source_market_caps_parsed']}/130; unparsed/unavailable: {report['source_errors_or_unparsed']}/130.")
    print("Retrieved source ranges:",report["source_range_counts"])
    print("Quote-as-of independently verified: 0/130; qualified Pipeline: UNKNOWN.")

if __name__ == "__main__":
    if len(sys.argv)!=2:
        sys.exit("Usage: refresh_phase3_130_nasdaq_research.py <report.json>")
    main(Path(sys.argv[1]))
