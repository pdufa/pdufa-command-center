#!/usr/bin/env python3
"""Refresh saved SEC Step 4 cash-only runway for eligible GEM research tickers.

No finding here verifies a trade entry, a financing close, a prediction or a
live SEC filing alert. A failed SEC request never reuses stale cash as current.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sec_step4 import load_registry, scan_one  # noqa: E402

RESOLVED = {"APPROVED", "CRL", "REJECTED", "WITHDRAWN", "REFUSED"}
PHASE3_VERIFIED = {"VERIFIED_SUCCESS", "PRIMARY_MET_VERIFIED"}
PACIFIC = ZoneInfo("America/Los_Angeles")


def day(raw):
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except (TypeError, ValueError):
        return None


def eligible_tickers(rows, registry, *, as_of, limit=75):
    """A deterministic SEC-registered Phase 3 research subset, never fuzzy-joined."""
    eligible = {}
    ambiguous = set()
    events = set()
    for row in rows:
        event_key = str(row.get("event_key") or "").strip()
        ticker = str(row.get("ticker") or "").strip().upper()
        phase3 = day(row.get("phase3_date"))
        pdufa = day(row.get("pdufa_date"))
        if not event_key or event_key in events:
            if event_key:
                ambiguous.add(event_key)
            continue
        events.add(event_key)
        if (str(row.get("phase3_status") or "").strip().upper() not in PHASE3_VERIFIED
                or not phase3 or phase3 > as_of
                or not pdufa or pdufa < as_of + timedelta(days=4)
                or str(row.get("outcome") or "").strip().upper() in RESOLVED
                or str(row.get("monitor_eligibility") or "").strip().upper() == "EXCLUDED"
                or not ticker or not event_key.startswith(ticker + "|")
                or ticker not in registry or registry[ticker].get("conflict")
                or not registry[ticker].get("cik")):
            continue
        if ticker not in eligible or pdufa < eligible[ticker][0]:
            eligible[ticker] = (pdufa, event_key)
    eligible = {ticker: pair for ticker, pair in eligible.items()
                if pair[1] not in ambiguous}
    return [ticker for ticker, _ in sorted(
        eligible.items(), key=lambda x: (x[1][0], x[0])
    )[:limit]]


def read_candidates(path):
    try:
        with Path(path).open(newline="", encoding="utf-8-sig") as fp:
            return list(csv.DictReader(fp))
    except (OSError, UnicodeError, csv.Error):
        return []


def old_history(path):
    """Preserve observations as history only, never as fresh source evidence."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if (data.get("schema_version") != 1
                or data.get("source") != "SEC_STEP4_COMPANYFACTS"):
            return []
        values = data.get("history", []) + data.get("snapshots", [])
        return [s for s in values if isinstance(s, dict)]
    except (OSError, UnicodeError, ValueError, TypeError, AttributeError):
        return []


def archive_history(prior, current, *, per_ticker=8):
    newest = {}
    for snap in current:
        if isinstance(snap, dict):
            newest[str(snap.get("ticker") or "").upper()] = snap
    results = {}
    for snap in prior:
        ticker = str(snap.get("ticker") or "").upper()
        if not ticker or not isinstance(snap.get("evidence"), dict):
            continue
        if ticker in newest and snap == newest[ticker]:
            continue
        period = (snap.get("evidence", {}).get("cash") or {}).get("period_end")
        key = (str(period), str(snap.get("as_of") or ""))
        results.setdefault(ticker, {})[key] = snap
    return [
        item for ticker in sorted(results)
        for _, item in sorted(results[ticker].items(), reverse=True)[:per_ticker]
    ]


def collect(data_dir, *, as_of, limit=75, agent=None, scanner=scan_one):
    """Return a machine-readable report; failures remove current evidence."""
    data_dir = Path(data_dir)
    registry = load_registry(data_dir / "company_registry.csv")
    rows = read_candidates(data_dir / "pdufa_candidates.csv")
    symbols = eligible_tickers(rows, registry, as_of=as_of, limit=limit)
    output_file = data_dir / "gem_runway_evidence.json"
    previous = old_history(output_file)
    successes = []
    failures = []
    agent = agent if agent is not None else os.getenv("SEC_USER_AGENT", "")
    if symbols and ("@" not in agent or len(agent.strip()) < 12):
        failures = [{"ticker": ticker, "reason": "SEC contact identity unavailable"}
                    for ticker in symbols]
    else:
        for ticker in symbols:
            try:
                _, snapshot = scanner(
                    ticker, registry=registry, user_agent=agent,
                    db_path=data_dir / "sec_step4_snapshots.sqlite3",
                    as_of=as_of,
                )
                if snapshot.get("ticker") != ticker or snapshot.get("as_of") != as_of.isoformat():
                    raise ValueError("SEC scan returned mismatched ticker/as-of")
                successes.append(snapshot)
            except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
                failures.append({"ticker": ticker, "reason": str(exc)[:300]})
    report = {
        "schema_version": 1,
        "source": "SEC_STEP4_COMPANYFACTS",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of_pacific": as_of.isoformat(),
        "collector_status": "COMPLETE" if not failures else "PARTIAL — SOURCE FAILURES",
        "target_count": len(symbols), "collected_count": len(successes),
        "failures": failures,
        "snapshots": successes,
        "history": archive_history(previous, successes),
        "caveat": ("SEC source-linked cash-only runway is based on historical operating "
                   "burn. It does not verify later financings or future liquidity."),
    }
    data_dir.mkdir(parents=True, exist_ok=True)
    tmp = output_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(output_file)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--max-tickers", type=int, default=75)
    parser.add_argument("--as-of", type=str)
    args = parser.parse_args(argv)
    if not 1 <= args.max_tickers <= 75:
        parser.error("--max-tickers must be 1–75")
    today = day(args.as_of) if args.as_of else datetime.now(PACIFIC).date()
    if today is None:
        parser.error("--as-of requires YYYY-MM-DD")
    try:
        result = collect(args.data_dir, as_of=today, limit=args.max_tickers)
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as exc:
        parser.error("Runway collector source failure: " + str(exc))
    print(json.dumps({k: result[k] for k in (
        "collector_status", "target_count", "collected_count", "failures"
    )}, sort_keys=True))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
