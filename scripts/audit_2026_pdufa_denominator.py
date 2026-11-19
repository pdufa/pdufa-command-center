#!/usr/bin/env python3
"""Audit a claimed annual PDUFA denominator against the tracked blind-assessment cohort.

This does not certify that a claimed total is a verified event count. It reports
the difference and refuses to call untracked events "missing" until a canonical
deduplicated full-year event manifest is supplied.

Usage:
  python scripts/audit_2026_pdufa_denominator.py --claimed-total 296
  python scripts/audit_2026_pdufa_denominator.py --claimed-total 296 --full-year-csv path/to/events.csv --id-column event_id

A canonical full-year CSV should have a unique event key representing
application + supplement + indication + review cycle, not just a drug name.
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "data/backtest/2026-clinical-evidence-backlog.csv"
COVERAGE = ROOT / "data/backtest/2026-level01-06-blind-assessment-coverage.csv"

def read_rows(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claimed-total", type=int, required=True)
    p.add_argument("--full-year-csv", type=Path)
    p.add_argument("--id-column", default="event_id")
    args = p.parse_args()
    if args.claimed_total <= 0:
        p.error("--claimed-total must be positive")
    backlog = read_rows(BACKLOG)
    coverage = read_rows(COVERAGE)
    ids = [r["event_id"] for r in backlog]
    if len(set(ids)) != len(ids):
        raise SystemExit("ERROR: duplicate event IDs in backlog")
    tracked = set(ids)
    complete_six = Counter(r["event_id"] for r in coverage
                           if r["level"] in {f"L{i:02d}" for i in range(1, 7)})
    fully_tracked = sum(complete_six[x] == 6 for x in tracked)
    locked = {r["event_id"] for r in coverage
              if r["prediction_lock_status"] != "NOT_LOCKED"
              and r["blind_prediction"] != "NOT_ISSUED"}
    print(f"User-claimed 2026 denominator (UNVERIFIED): {args.claimed_total}")
    print(f"Unique tracked event IDs: {len(tracked)}")
    print(f"Events with six level-tracking rows: {fully_tracked}")
    print(f"Events with at least one non-default prediction lock: {len(locked)} (NOT proof of valid blind prediction)")
    print(f"Arithmetic denominator gap: {args.claimed_total - len(tracked)} (NOT a verified missing-event count)")
    if not args.full_year_csv:
        print("DENOMINATOR NOT RECONCILED: supply --full-year-csv with verified canonical event keys.")
        return 1
    all_rows = read_rows(args.full_year_csv)
    if any(args.id_column not in r for r in all_rows):
        raise SystemExit(f"ERROR: full-year CSV missing {args.id_column!r}")
    full_ids = [r[args.id_column].strip() for r in all_rows]
    if not all(full_ids) or len(set(full_ids)) != len(full_ids):
        raise SystemExit("ERROR: empty/duplicate full-year event keys; canonical deduplication required")
    full = set(full_ids)
    print(f"Unique full-year keys: {len(full)}")
    print(f"Full-year keys absent from tracked backlog: {len(full - tracked)}")
    print(f"Tracked keys absent from full-year file: {len(tracked - full)}")
    print(f"Full-year total matches claimed count: {len(full) == args.claimed_total}")
    if full - tracked:
        print("UNTRACKED KEYS:")
        for event_id in sorted(full - tracked):
            print(event_id)
    return 0 if full == tracked and len(full) == args.claimed_total else 1

if __name__ == "__main__":
    raise SystemExit(main())
