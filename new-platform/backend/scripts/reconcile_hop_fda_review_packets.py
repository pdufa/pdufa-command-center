"""Offline comparison of two FDA source-review claims; never clears approval gates."""
from __future__ import annotations

import argparse
import json
from datetime import date

from app.hop_fda_dual_review_packets import load_unreviewed_worksheet
from app.hop_fda_reviewer_reconciliation import (
    load_completed_or_blank_packet, reconcile_review_claims,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find incomplete/disagreeing independent-review *claims*; no adjudication"
    )
    parser.add_argument("original_worksheet_csv", help="Original unmodified source review worksheet")
    parser.add_argument("first_reviewer_csv", help="First reviewer response, or blank packet")
    parser.add_argument("second_reviewer_csv", help="Second reviewer response, or blank packet")
    parser.add_argument("--as-of", required=True, type=date.fromisoformat,
                        help="Calendar cutoff YYYY-MM-DD for future-date rejection")
    args = parser.parse_args()

    result = reconcile_review_claims(
        load_unreviewed_worksheet(args.original_worksheet_csv),
        load_completed_or_blank_packet(args.first_reviewer_csv),
        load_completed_or_blank_packet(args.second_reviewer_csv),
        as_of=args.as_of,
    )
    # Never expose reviewer names or prose, only source-record hashes and field names.
    print(json.dumps(result, indent=2, sort_keys=True))
    # Intentionally never exits with a "verified" success code: this tool is
    # incapable of authenticated human adjudication even for matching claims.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
