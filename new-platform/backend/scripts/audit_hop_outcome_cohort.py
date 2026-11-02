"""Audit staged HOP outcome CSV claims without fitting or releasing a model."""
from __future__ import annotations

import argparse
import json
from datetime import date

from app.hop_outcome_audit import audit_quarantined_outcome_intake
from app.hop_outcomes_import import validate_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report unverified historical FDA outcome CSV claims and release blockers"
    )
    parser.add_argument("csv_file", help="Local manually curated CSV; never uploaded")
    parser.add_argument(
        "--as-of", required=True, type=date.fromisoformat,
        help="CSV audit cutoff, not a prediction timestamp (YYYY-MM-DD)",
    )
    args = parser.parse_args()
    intake = validate_csv(args.csv_file, as_of=args.as_of)
    report = audit_quarantined_outcome_intake(intake)
    # No row-level identities or clinical records are printed.
    print(json.dumps(report, sort_keys=True, indent=2))
    # Success means only that quarantined CSV formatting was internally coherent.
    # An empty/invalid/partially rejected file returns a failing exit code.
    return 0 if intake["status"] == "SCHEMA_VALIDATED_REVIEW_REQUIRED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
