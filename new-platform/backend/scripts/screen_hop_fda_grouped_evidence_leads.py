"""Offline screening of human-filled original FDA source-lead research packets.

Reconstructs packet IDs from a private source-letter queue and the pinned,
real aggregate audit. This does NOT authenticate any FDA PDF, adjudicator,
review cycle, or outcome and deliberately exits nonzero.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from app.hop_fda_gap_research_packets import (
    build_source_search_packets, screen_private_evidence_leads,
)

PINNED_AUDIT = (Path(__file__).resolve().parents[1] / "app" /
                "research_sources" / "hop_fda_unmatched_letter_gap_audit_20261025.json")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Screen manually attached official FDA source leads WITHOUT labeling outcomes"
    )
    parser.add_argument("--private-unverified-letter-queue", type=Path, required=True)
    parser.add_argument("--submitted-grouped-research-packets", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, required=True)
    parser.add_argument("--private-output-json", type=Path, required=True)
    args = parser.parse_args()
    pinned = json.loads(PINNED_AUDIT.read_text(encoding="utf-8"))
    queue = json.loads(args.private_unverified_letter_queue.read_text(encoding="utf-8"))
    claimed = json.loads(
        args.submitted_grouped_research_packets.read_text(encoding="utf-8")
    )
    baseline, _ = build_source_search_packets(
        queue, as_of=args.as_of, pinned_audit=pinned,
    )
    screening = screen_private_evidence_leads(baseline, claimed)
    args.private_output_json.parent.mkdir(parents=True, exist_ok=True)
    args.private_output_json.write_text(
        json.dumps(screening, indent=2, sort_keys=True) + "\n",
        encoding="utf-8"
    )
    print(json.dumps(screening, indent=2, sort_keys=True))
    # URL validation is NOT original FDA source authentication.
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
