"""Read-only quarantined outcome-to-source crosscheck; no FDA verification."""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_fda_review_triage import TRIAGE_FIELDS
from app.hop_fda_cycle_claim_register import FIELDS, read_csv
from app.hop_fda_outcome_source_crosscheck import crosscheck_historical_outcome_claims
from app.hop_outcomes_import import validate_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare historical FDA outcome claims with unverified cycle worklist"
    )
    parser.add_argument("historical_outcomes_csv", type=Path)
    parser.add_argument("unverified_source_queue_csv", type=Path)
    parser.add_argument("unverified_cycle_claim_register_csv", type=Path)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    outcome_intake = validate_csv(args.historical_outcomes_csv, as_of=args.as_of)
    queue = read_csv(args.unverified_source_queue_csv, TRIAGE_FIELDS)
    claims = read_csv(args.unverified_cycle_claim_register_csv, FIELDS)
    diagnostic = crosscheck_historical_outcome_claims(
        outcome_intake, queue, claims, as_of=args.as_of
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "unverified_outcome_source_crosscheck.json").write_text(
        json.dumps(diagnostic, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": diagnostic["status"],
        "staged_historical_outcome_rows": diagnostic["staged_historical_outcome_rows"],
        "diagnostic_reason_counts": diagnostic["diagnostic_reason_counts"],
        "independent_fda_review_cycle_decisions_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
    }, indent=2, sort_keys=True))
    # Matching claim text is not independent FDA evidence verification.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
