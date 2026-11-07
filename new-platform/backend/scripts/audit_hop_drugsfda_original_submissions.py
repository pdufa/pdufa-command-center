"""Analyze extracted FDA Drugs@FDA Applications/Submissions TSVs OFFLINE.

Does not fetch FDA data or convert status codes to FDA decision outcomes.
Private CSVs and reports remain local. No research validation is implied.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_drugsfda_submission_spine import audit_original_submissions


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stage original NDA/BLA submission-history references, NOT FDA decisions"
    )
    parser.add_argument("applications_tsv", type=Path)
    parser.add_argument("submissions_tsv", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True,
                        help="Historical source-audit cutoff YYYY-MM-DD")
    parser.add_argument("--output-json", type=Path, required=True,
                        help="LOCAL private output only; large when source tables are large")
    args = parser.parse_args()
    result = audit_original_submissions(
        args.applications_tsv, args.submissions_tsv, as_of=args.as_of,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        key: result[key] for key in (
            "status", "application_rows_in_extract", "submission_rows_in_extract",
            "original_nda_bla_submission_rows",
            "distinct_nda_bla_applications_in_original_submission_inventory",
            "source_data_quality_flag_counts",
            "independently_verified_fda_review_cycles",
            "complete_original_nda_bla_application_denominator_verified",
            "model_eligible_records", "prediction_probability", "readiness",
        )
    }, indent=2, sort_keys=True))
    # Source-history completeness != original application decision completeness.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
