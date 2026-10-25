"""Offline HOP CSV schema inspection. No FDA fetching, DB writes or model fitting."""
from __future__ import annotations

import argparse
import json
from datetime import date

from app.hop_outcomes_import import validate_csv


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect quarantined HOP outcome CSV format")
    parser.add_argument("csv_file", help="Manually sourced outcome CSV")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat,
                        help="Import cutoff in YYYY-MM-DD; never a prediction cutoff")
    args = parser.parse_args()
    report = validate_csv(args.csv_file, as_of=args.as_of)
    # Deliberately omit patient/trial/source content; only report counts and row-level blockers.
    print(json.dumps({
        key: value for key, value in report.items() if key != "records"
    }, indent=2, sort_keys=True))
    return 1 if report["status"] != "SCHEMA_VALIDATED_REVIEW_REQUIRED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
