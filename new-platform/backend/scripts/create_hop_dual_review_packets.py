"""Prepare two separate offline blank FDA page-source review packets.

Does not collect source data, authenticate reviewers or adjudicate FDA outcomes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.hop_fda_dual_review_packets import (
    build_dual_review_packets, load_unreviewed_worksheet, packet_csv,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Split the UNADJUDICATED FDA page-review worksheet into blank reviewer packets"
    )
    parser.add_argument("worksheet_csv", help="Original, unmodified FDA page evidence worksheet")
    parser.add_argument("--output-dir", required=True, help="Existing or new LOCAL output directory")
    args = parser.parse_args()

    rows = load_unreviewed_worksheet(args.worksheet_csv)
    first, second, audit = build_dual_review_packets(rows)
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "first_independent_review_blank.csv").write_text(
        packet_csv(first), encoding="utf-8"
    )
    (destination / "second_independent_review_blank.csv").write_text(
        packet_csv(second), encoding="utf-8"
    )
    (destination / "dual_review_packet_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
