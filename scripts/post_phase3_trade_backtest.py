#!/usr/bin/env python3
"""Stage 3 CLI: run audited offline hypotheses, never manufacture price history.

Usage:
 python scripts/post_phase3_trade_backtest.py --output-dir output/post_phase3_stage3
 python scripts/post_phase3_trade_backtest.py --events PATH --bars PATH --output-dir PATH
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from post_phase3_trade_backtest import (  # noqa: E402
    BAR_FIELDS, EVENT_FIELDS, SUMMARY_FIELDS, TRADE_FIELDS,
    read_csv, run_backtest,
)


def write_csv(path, columns, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def checked_rows(path, required_columns):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Missing audited input: {path}")
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        header = csv.reader(handle)
        try:
            columns = next(header)
        except StopIteration:
            raise ValueError(f"Missing CSV header: {path}") from None
        if len(columns) != len(set(columns)) or not set(required_columns).issubset(columns):
            raise ValueError(f"Incorrect or duplicate CSV fields: {path}")
    return read_csv(path)


def source_inventory():
    # Counts only; present-day sources are NOT silently promoted to
    # historical point-in-time entry eligibility or OHLCV proof.
    source_files = {
        "regulatory_ledger": "pdufa_candidates.csv",
        "current_second_financing_ledger": "second_financing_status.csv",
        "current_market_snapshots": "step7_market_status.csv",
        "current_phase3_registry": "phase3_announcements.csv",
    }
    return {key:len(read_csv(ROOT/"data"/filename)) for key,filename in source_files.items()}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=Path,
                        default=ROOT/"data/post_phase3_historical_trade_events.csv")
    parser.add_argument("--bars", type=Path,
                        default=ROOT/"data/post_phase3_historical_adjusted_ohlcv.csv")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--min-daily-dollars", type=float, default=250000.0)
    parser.add_argument("--slippage-bps", type=float, default=10)
    args = parser.parse_args(argv)
    try:
        events = checked_rows(args.events, EVENT_FIELDS)
        bars = checked_rows(args.bars, BAR_FIELDS)
        trades, summary, audit = run_backtest(
            events, bars, min_daily_dollars=args.min_daily_dollars,
            slippage_bps=args.slippage_bps,
        )
    except ValueError as exc:
        parser.error(str(exc))
    audit["present_day_source_inventory_NOT_BACKTEST_EVIDENCE"] = source_inventory()
    audit["methodology"] = {
        "price_entries":"Next available session OPEN strictly after all required public evidence; no same-day lookahead.",
        "price_exits":"Last actual session CLOSE no later than PDUFA minus 30/14/7 calendar days.",
        "price_adjustment":"All bars must affirm SPLIT_ADJUSTED_VERIFIED with HTTPS source.",
        "liquidity":"Twenty prior sessions' mean close-times-volume only, excludes entry-day volume.",
        "base":"After second financing disclosure: >=10 complete sessions, last 10 close spread <=15%, recent five-volume / prior20-volume 0.5 to 1.25; buy no earlier than next OPEN.",
        "slippage_per_leg_bps": args.slippage_bps,
        "min_prior20_daily_dollar_volume": args.min_daily_dollars,
        "early_fda_action":"CENSORED, counted explicitly; tail risk not represented in return distribution.",
        "population":"Comparators conditional on eventual verified two distinct post-phase3 financing closings.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir/"per_event_scenarios.csv", TRADE_FIELDS, trades)
    write_csv(args.output_dir/"scenario_summary.csv", SUMMARY_FIELDS, summary)
    (args.output_dir/"readiness_and_blockers.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({
        "status":audit["status"], "audited_event_rows":audit["event_rows"],
        "historical_ohlcv_rows":audit["price_rows"],
        "completed_scenarios":audit["completed_scenarios"],
        "early_action_censored":audit["early_action_censored_scenarios"],
        "output_dir":str(args.output_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
