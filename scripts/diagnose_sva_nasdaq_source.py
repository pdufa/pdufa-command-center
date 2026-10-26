#!/usr/bin/env python3
"""Isolated, bounded original-source SVA Nasdaq endpoint diagnostic.

No replacement market caps, no third-party data, no Pipeline qualification.
A source error is recorded, never silently treated as a cap or a delisting.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

URL = "https://api.nasdaq.com/api/quote/SVA/summary?assetclass=stocks"
MAX_BYTES = 300_000


def diagnose():
    report = {"ticker": "SVA", "original_source": URL,
              "checked_at_utc": datetime.now(timezone.utc).isoformat(),
              "independently_verified_market_cap": None,
              "exchange_quote_timestamp_verified": False,
              "qualified_pipeline": None}
    try:
        request = urllib.request.Request(URL, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; PDUFA-Research-ReadOnly/1.0)",
        })
        with urllib.request.urlopen(request, timeout=12) as response:
            report["http_status"] = response.status
            report["content_type"] = response.headers.get("Content-Type", "")
            report["final_url_matches_original"] = response.geturl() == URL
            raw = response.read(MAX_BYTES + 1)
        report["response_bytes"] = len(raw)
        if len(raw) > MAX_BYTES:
            report["disposition"] = "OVERSIZE_RESPONSE"
        elif report["http_status"] != 200 or not report["final_url_matches_original"]:
            report["disposition"] = "UNEXPECTED_HTTP_OR_REDIRECT"
        elif "json" not in report["content_type"].lower():
            report["disposition"] = "NON_JSON_RESPONSE"
        else:
            report["source_sha256"] = hashlib.sha256(raw).hexdigest()
            payload = json.loads(raw)
            data = payload.get("data") if isinstance(payload, dict) else None
            report["nasdaq_status"] = payload.get("status") if isinstance(payload, dict) else None
            report["data_present"] = isinstance(data, dict)
            report["returned_symbol"] = data.get("symbol") if isinstance(data, dict) else None
            summary = data.get("summaryData") if isinstance(data, dict) else None
            cap = summary.get("MarketCap") if isinstance(summary, dict) else None
            report["market_cap_field_present"] = cap is not None
            report["disposition"] = ("ORIGINAL_SOURCE_CAP_FIELD_PRESENT_NEEDS_VALIDATION"
                                     if cap is not None else "ORIGINAL_SOURCE_MISSING_MARKET_CAP")
    except urllib.error.HTTPError as exc:
        report.update({"disposition": "ORIGINAL_SOURCE_HTTP_ERROR", "http_status": exc.code,
                       "error_type": type(exc).__name__})
    except Exception as exc:
        report.update({"disposition": "ORIGINAL_SOURCE_ERROR", "error_type": type(exc).__name__})
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: diagnose_sva_nasdaq_source.py <report.json>")
    output = Path(sys.argv[1])
    report = diagnose()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SVA original-source disposition:", report["disposition"])
    print("HTTP status:", report.get("http_status", "not available"))
    print("Source market-cap field present:", report.get("market_cap_field_present", "not established"))
    print("SVA independently verified cap: UNKNOWN. Qualified Pipeline: UNKNOWN.")
