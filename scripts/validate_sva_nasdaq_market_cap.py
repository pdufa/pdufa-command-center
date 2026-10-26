#!/usr/bin/env python3
"""Validate original Nasdaq SVA numeric cap; never infer quote-time freshness.

Read-only one-source check, no saved quote mutation, Pipeline promotion or trade.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request

from recheck_phase3_nasdaq_market_caps import parse_cap, MIN_CAP, MAX_CAP

URL = "https://api.nasdaq.com/api/quote/SVA/summary?assetclass=stocks"
MAX_BYTES = 300_000


def check():
    report = {
        "ticker": "SVA", "original_source": URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "numeric_cap_verified_from_original_response": False,
        "exchange_quote_timestamp_verified": False,
        "qualified_pipeline": None,
    }
    try:
        request = urllib.request.Request(URL, headers={
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; PDUFA-Research-ReadOnly/1.0)",
        })
        with urllib.request.urlopen(request, timeout=12) as response:
            if response.status != 200 or response.geturl() != URL or "json" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Untrusted Nasdaq response")
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Oversize original response")
        payload = json.loads(raw)
        cap = parse_cap(payload, "SVA")
        report.update({
            "numeric_cap_verified_from_original_response": True,
            "market_cap_usd_at_retrieval": cap,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "range_at_retrieval": "IN_RANGE" if MIN_CAP <= cap <= MAX_CAP else ("BELOW_300M" if cap < MIN_CAP else "ABOVE_10B"),
            "disposition": "NUMERIC_CAP_VALIDATED_QUOTE_TIME_NOT_VERIFIED",
        })
    except Exception as exc:
        report.update({"disposition": "NUMERIC_CAP_UNRESOLVED", "error_type": type(exc).__name__})
    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: validate_sva_nasdaq_market_cap.py <report.json>")
    report = check()
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SVA numeric cap validated:", report["numeric_cap_verified_from_original_response"])
    print("SVA numeric cap USD:", report.get("market_cap_usd_at_retrieval", "UNRESOLVED"))
    print("SVA saved-range check:", report.get("range_at_retrieval", "UNRESOLVED"))
    print("SVA exchange quote timestamp verified: False. Qualified Pipeline: UNKNOWN.")
