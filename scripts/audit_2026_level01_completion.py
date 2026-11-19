#!/usr/bin/env python3
"""Audit whether Level 1 is *actually complete* for a claimed 2026 PDUFA universe.

A screening record is not a completed verified L1 assessment. Exit status 1
until every canonical event has independently verified identity and cutoff,
a documented reviewer exposure attestation and a completed L1 disposition.
Does not invent the missing 207 events or treat abstention as a prediction.

Usage: python scripts/audit_2026_level01_completion.py --target 296
"""
import argparse
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data/backtest/2026-level01-identity-screening.csv"
NEEDED = ("event_id", "level", "drug", "indication", "application_number",
          "review_cycle", "research_cutoff_date", "identity_screen",
          "researcher_outcome_exposure", "assessment", "blind_prediction",
          "prediction_lock_status")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", type=int, default=296)
    p.add_argument("--screen", type=Path, default=SCREEN)
    args = p.parse_args()
    if args.target <= 0:
        p.error("target must be positive")
    with args.screen.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = set(NEEDED) - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Missing required columns: {sorted(missing)}")
        rows = list(reader)
    ids = [r["event_id"] for r in rows]
    if not all(ids) or len(ids) != len(set(ids)):
        raise SystemExit("Duplicate/blank candidate event IDs")
    if any(r["level"] != "L01" for r in rows):
        raise SystemExit("Unexpected level in Level 1 screening")
    status = Counter(r["identity_screen"] for r in rows)
    source_complete = sum(all(r.get(k, "").strip() for k in
                              ("drug", "indication", "application_number", "review_cycle",
                               "research_cutoff_date")) for r in rows)
    # Existing screen contains only PROVISIONAL identity or incomplete identity.
    # Neither is proof of source-verified application/review-cycle linkage.
    verified = sum(r["identity_screen"] == "VERIFIED_SOURCE_AUTHENTICATED"
                   and r["researcher_outcome_exposure"] == "INDEPENDENTLY_ATTESTED_UNEXPOSED"
                   and r["assessment"] not in ("", "NOT_REVIEWED")
                   for r in rows)
    print(f"Requested annual target (unverified): {args.target}")
    print(f"Level 1 candidate screening rows: {len(rows)}")
    print(f"Rows with all provisional identity fields populated: {source_complete}")
    print(f"Screening statuses: {dict(status)}")
    print(f"Independently verified L1 completions: {verified}")
    print(f"Arithmetic target gap: {args.target - len(rows)}; not verified missing events")
    if len(rows) != args.target or verified != args.target:
        print("INCOMPLETE: cannot certify Level 1 for full requested universe")
        return 1
    print("L1 source and attestation fields meet declared completion gate")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
