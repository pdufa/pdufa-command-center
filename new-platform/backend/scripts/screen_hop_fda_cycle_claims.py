"""Prepare or screen unverified original-source FDA review-cycle claims offline.

The command does not adjudicate FDA actions or authorize model training.
No reviewer identities, evidence notes, or raw claims are printed in an audit.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_fda_review_triage import TRIAGE_FIELDS
from app.hop_fda_cycle_claim_register import (
    FIELDS, prepare_claim_register, read_csv, render_csv, screen_claim_register,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline FDA cycle-claim review register")
    parser.add_argument("unverified_source_queue_csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--submitted-register", type=Path,
                        help="Optional completed or partial *private* cycle-claim register")
    parser.add_argument("--as-of", type=date.fromisoformat,
                        help="Required for screening claims; YYYY-MM-DD")
    args = parser.parse_args()

    queue = read_csv(args.unverified_source_queue_csv, TRIAGE_FIELDS)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if args.submitted_register is None:
        rows = prepare_claim_register(queue)
        (args.output_dir / "blank_unverified_fda_cycle_claims.csv").write_text(
            render_csv(rows, FIELDS), encoding="utf-8"
        )
        audit = {
            "status": "BLANK_UNVERIFIED_FDA_CYCLE_REGISTER_PREPARED",
            "published_source_references": len(rows),
            "independently_verified_review_cycles": 0,
            "model_eligible_records": 0,
            "prediction_probability": None,
            "readiness": "REVIEW_REQUIRED",
        }
    else:
        if args.as_of is None:
            parser.error("--as-of is required for screening submitted claims")
        claims = read_csv(args.submitted_register, FIELDS)
        audit = screen_claim_register(queue, claims, as_of=args.as_of)
    (args.output_dir / "fda_cycle_claim_screening_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    # Intentional nonzero status: a locally valid claim can never be
    # independently verified, signed or model-authorized by this command.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
