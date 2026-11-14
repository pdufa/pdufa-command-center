"""Build a quarantined, priority-sorted FDA manual adjudication worklist.

No FDA fetching, reviewer identification, database updates, scoring or model
training. The referenced published-letter worksheet is NOT a complete
FDA approval/nonapproval cohort.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_fda_dual_review_packets import load_unreviewed_worksheet
from app.hop_fda_reviewer_reconciliation import (
    load_completed_or_blank_packet, reconcile_review_claims,
)
from app.hop_fda_review_triage import (
    build_review_triage, load_source_index, review_triage_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare read-only FDA source-review queue from unadjudicated CSVs"
    )
    parser.add_argument("original_worksheet_csv", help="Original unmodified FDA worksheet")
    parser.add_argument("first_reviewer_csv", help="First reviewer packet, blank or filled")
    parser.add_argument("second_reviewer_csv", help="Second reviewer packet, blank or filled")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--source-index", type=Path,
                        default=Path(__file__).resolve().parents[1] / "app" /
                        "research_sources" / "hop_fda_page_review_worksheet_audit_index.json")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="Private, local output directory; keep source reviews private")
    args = parser.parse_args()

    original = load_unreviewed_worksheet(args.original_worksheet_csv)
    first = load_completed_or_blank_packet(args.first_reviewer_csv)
    second = load_completed_or_blank_packet(args.second_reviewer_csv)
    source_index = load_source_index(args.source_index)
    comparison = reconcile_review_claims(original, first, second, as_of=args.as_of)
    queue, audit = build_review_triage(
        original, first, second, comparison, source_index, as_of=args.as_of,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "unverified_fda_review_queue.csv").write_text(
        review_triage_csv(queue), encoding="utf-8",
    )
    (args.output_dir / "unverified_fda_review_queue_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    # A syntactically valid and consistently ranked queue still has ZERO
    # authenticated regulatory outcomes, so review never succeeds here.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
