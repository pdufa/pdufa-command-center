"""Summarize committed FDA source coverage without inventing a decision cohort."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.hop_fda_cohort_coverage import (
    audit_fda_source_coverage, count_historical_template_rows,
    load_source_indexes,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline cross-index coverage report: FDA outcomes remain UNVERIFIED"
    )
    backend = Path(__file__).resolve().parents[1]
    parser.add_argument("--source-index-dir", type=Path,
                        default=backend / "app" / "research_sources")
    parser.add_argument("--historical-csv", type=Path,
                        default=backend / "data" / "hop_historical_outcomes_template.csv")
    parser.add_argument("--output-json", type=Path,
                        help="Optional local research-only report; never published automatically")
    args = parser.parse_args()
    report = audit_fda_source_coverage(
        load_source_indexes(args.source_index_dir),
        historical_template_rows=count_historical_template_rows(args.historical_csv),
    )
    result = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output_json is not None:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(result, encoding="utf-8")
    print(result, end="")
    # A structurally consistent source corpus is not a verified, complete FDA
    # application review-cycle population. Zero=quarantined, not release ready.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
