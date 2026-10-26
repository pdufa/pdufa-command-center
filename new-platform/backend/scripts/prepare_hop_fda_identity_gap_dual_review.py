"""Prepare two BLANK private FDA identity-gap source reviewer packet sets.

Neither a generated packet nor a future matching reviewer claim constitutes
independent adjudication of FDA outcome labels. Never upload private reviewer
data to a public GitHub Actions artifact or live database.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.hop_fda_identity_gap_dual_review import blank_identity_gap_dual_reviews


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare two independent empty FDA source reviewer handoff packets"
    )
    parser.add_argument("--private-enriched-packets", type=Path, required=True)
    parser.add_argument("--private-first-review-json", type=Path, required=True)
    parser.add_argument("--private-second-review-json", type=Path, required=True)
    parser.add_argument("--public-audit-json", type=Path, required=True)
    args = parser.parse_args()
    paths = (
        args.private_enriched_packets.resolve(), args.private_first_review_json.resolve(),
        args.private_second_review_json.resolve(), args.public_audit_json.resolve(),
    )
    if len(set(paths)) != len(paths):
        raise ValueError("FDA source reviewers and public audit must use distinct files")
    enriched = json.loads(args.private_enriched_packets.read_text(encoding="utf-8"))
    first, second, audit = blank_identity_gap_dual_reviews(enriched)
    if (audit["model_eligible_records"] != 0
            or audit["independent_reviews_completed"] != 0
            or audit["review_cycle_outcomes_verified"] != 0):
        raise ValueError("FDA source packets may never self-authorize model review")
    for path, obj in (
        (args.private_first_review_json, first),
        (args.private_second_review_json, second),
        (args.public_audit_json, audit),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0  # Source-blank packet generation only; NEVER outcome adjudication.


if __name__ == "__main__":
    raise SystemExit(main())
