#!/usr/bin/env python3
"""Read-only original Nasdaq market-cap recheck for 130 saved census tickers.

Never overwrite dated input, promote Pipeline eligibility, or invent missing data.
An HTTP success only confirms retrieval, not an exchange-stamped live quote.
"""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
MAX_BYTES = 300_000
MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000


def parse_cap(payload, ticker):
    if not isinstance(payload, dict) or payload.get("status", {}).get("rCode") not in (None, 200):
        raise ValueError("Invalid Nasdaq envelope")
    data = payload.get("data")
    if not isinstance(data, dict) or data.get("symbol", "").upper() != ticker:
        raise ValueError("Nasdaq ticker mismatch")
    summary = data.get("summaryData")
    if not isinstance(summary, dict):
        raise ValueError("Missing Nasdaq summary")
    entry = summary.get("MarketCap")
    value = entry.get("value") if isinstance(entry, dict) else None
    if not isinstance(value, str):
        raise ValueError("Missing numeric market cap")
    normalized = value.strip().replace("$", "").replace(",", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([KMBT]?)", normalized, re.I)
    if not match:
        raise ValueError("Unparseable Nasdaq market cap")
    cap = float(match.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[match.group(2).upper()]
    if not (0 < cap < float("inf")):
        raise ValueError("Invalid Nasdaq cap")
    return cap


def audit(output):
    with TRIALS.open(encoding="utf-8-sig", newline="") as f:
        trials = list(csv.DictReader(f))
    tickers = sorted({r["ticker"] for r in trials})
    if len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741 or len(tickers) != 130:
        raise ValueError("Original 741/130 census not reconciled")
    rows = []
    for ticker in tickers:
        url = f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
        result = {"ticker": ticker, "source": url, "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                  "independent_retrieval_succeeded": False, "source_quote_timestamp_verified": False,
                  "qualified_pipeline": None}
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; PDUFA-Research-ReadOnly/1.0)"})
            with urllib.request.urlopen(request, timeout=8) as response:
                if response.status != 200 or response.geturl() != url or "json" not in response.headers.get("Content-Type", "").lower():
                    raise ValueError("Nasdaq source response not trusted")
                raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("Nasdaq response exceeds bound")
            cap = parse_cap(json.loads(raw), ticker)
            result.update({"independent_retrieval_succeeded": True, "market_cap_usd_at_retrieval": cap,
                           "source_sha256": hashlib.sha256(raw).hexdigest(),
                           "range_at_retrieval": "IN_RANGE" if MIN_CAP <= cap <= MAX_CAP else ("BELOW_300M" if cap < MIN_CAP else "ABOVE_10B"),
                           "disposition": "RETRIEVED_QUOTE_TIMESTAMP_NOT_VERIFIED"})
        except Exception as exc:
            result.update({"disposition": "SOURCE_UNAVAILABLE_OR_INVALID", "error_type": type(exc).__name__})
        rows.append(result)
        time.sleep(0.15)
    report = {"scope": "RESEARCH_ONLY_NOT_PIPELINE", "audit_at_utc": datetime.now(timezone.utc).isoformat(),
              "issuer_denominator": 130, "attempted": len(rows),
              "retrieved": sum(r["independent_retrieval_succeeded"] for r in rows),
              "unavailable": sum(not r["independent_retrieval_succeeded"] for r in rows),
              "exchange_quote_timestamp_verified": 0, "qualified_pipeline_count": None,
              "notes": "Retrieval time is NOT exchange quote time; source values may be delayed. No trade or FDA/PDUFA qualification.",
              "issuers": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Original Nasdaq summary retrieval:", report["retrieved"], "/130; unavailable:", report["unavailable"], "/130.")
    print("Exchange quote timestamp independently verified: 0/130. Qualified Pipeline: UNKNOWN.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: recheck_phase3_nasdaq_market_caps.py <report.json>")
    audit(Path(sys.argv[1]))
