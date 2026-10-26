#!/usr/bin/env python3
"""Audit dated 130-company cap snapshots, never present them as fresh prices.

No network or mutations. All 130 original census companies are checked.
This report is a historical snapshot audit, not a live market-cap check,
and it cannot promote candidates to the qualified Pipeline.
"""
import csv
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TRIALS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
CAPS = ROOT / "data/phase_pipeline_market_caps.csv"
LOW = 300_000_000
HIGH = 10_000_000_000
MAX_AGE = timedelta(hours=24)


def audit(now):
    trials = list(csv.DictReader(TRIALS.open(encoding="utf-8-sig", newline="")))
    caps = list(csv.DictReader(CAPS.open(encoding="utf-8-sig", newline="")))
    tickers = {r["ticker"] for r in trials}
    if len(trials) != 741 or len({r["nct_id"] for r in trials}) != 741 or len(tickers) != 130:
        raise ValueError("741-trial original census not reconciled")
    by_ticker = {}
    for row in caps:
        ticker = row["ticker"]
        if ticker in by_ticker:
            raise ValueError("Duplicate dated market-cap snapshot ticker")
        by_ticker[ticker] = row
    if not tickers.issubset(by_ticker):
        raise ValueError("Missing original census issuer snapshot")
    outcomes = []
    for ticker in sorted(tickers):
        row = by_ticker[ticker]
        if row["market_cap_source"] != f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks":
            raise ValueError("Unrecognized dated market-cap source URL")
        try:
            cap = float(row["market_cap"])
            checked = datetime.fromisoformat(row["market_cap_checked_at"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Malformed saved snapshot value or timestamp") from exc
        if not (0 <= cap < float("inf")) or checked.tzinfo is None or checked > now:
            raise ValueError("Invalid saved cap or timestamp")
        age = now - checked
        if row["market_cap_status"] != "VERIFIED":
            classification = "SAVED_SNAPSHOT_NOT_VERIFIED"
        elif age > MAX_AGE:
            classification = "STALE_SNAPSHOT_RECHECK_REQUIRED"
        elif cap < LOW:
            classification = "DATED_SNAPSHOT_BELOW_300M"
        elif cap > HIGH:
            classification = "DATED_SNAPSHOT_ABOVE_10B"
        else:
            classification = "DATED_SNAPSHOT_IN_RANGE_NOT_LIVE_VERIFIED"
        outcomes.append({
            "ticker": ticker, "dated_market_cap_usd": cap,
            "dated_source": row["market_cap_source"],
            "dated_checked_at": row["market_cap_checked_at"],
            "age_hours_at_audit": round(age.total_seconds() / 3600, 3),
            "dated_snapshot_range": "IN_RANGE" if LOW <= cap <= HIGH else ("BELOW" if cap < LOW else "ABOVE"),
            "research_freshness_disposition": classification,
            "live_market_cap_verified": False,
            "qualified_pipeline": None,
        })
    counts = {label: sum(r["research_freshness_disposition"] == label for r in outcomes)
              for label in ("SAVED_SNAPSHOT_NOT_VERIFIED", "STALE_SNAPSHOT_RECHECK_REQUIRED",
                            "DATED_SNAPSHOT_BELOW_300M", "DATED_SNAPSHOT_ABOVE_10B",
                            "DATED_SNAPSHOT_IN_RANGE_NOT_LIVE_VERIFIED")}
    return {
        "report_type": "HISTORICAL_130_ISSUER_MARKET_CAP_SNAPSHOT_AUDIT",
        "audited_at_utc": now.isoformat(),
        "original_census_trials": 741,
        "original_census_issuers": 130,
        "saved_issuer_snapshots_examined": len(outcomes),
        "saved_snapshot_range_counts": {
            "in_range": sum(r["dated_snapshot_range"] == "IN_RANGE" for r in outcomes),
            "below_300m": sum(r["dated_snapshot_range"] == "BELOW" for r in outcomes),
            "above_10b": sum(r["dated_snapshot_range"] == "ABOVE" for r in outcomes),
        },
        "freshness_dispositions": counts,
        "live_market_cap_verified_count": 0,
        "qualified_pipeline_count": None,
        "issuers": outcomes,
        "limitations": "Historical saved market-cap source values, NOT independently refreshed Nasdaq quotes. No drug rights or FDA/PDUFA qualification.",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: audit_phase3_marketcap_snapshot_freshness.py <output.json>")
    report = audit(datetime.now(timezone.utc))
    output = Path(sys.argv[1])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Dated original market-cap snapshots examined:", report["saved_issuer_snapshots_examined"], "/130")
    print("Historical range:", report["saved_snapshot_range_counts"])
    print("Freshness dispositions:", report["freshness_dispositions"])
    print("Live independent market-cap verification: 0/130. Qualified Pipeline: UNKNOWN.")
