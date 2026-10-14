#!/usr/bin/env python3
"""Export every Phase 3/financing-block program for nightly research follow-up.

This is a SAVED-SOURCE reconciliation, plus links to primary-source research.
Additional live registry/SEC source rechecks are separately archived by workflow.
Never authorize trade entry or imply that web links were followed.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gem_financing_batch_review import build_financing_review


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path, default=Path("reports/gem_financing_batch"))
    parser.add_argument("--as-of", type=date.fromisoformat, default=None)
    args = parser.parse_args(argv)
    today = args.as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    rows, summary = build_financing_review(args.data_dir, as_of=today)
    if not rows:
        parser.error("Financing ledger is empty or inaccessible; refuse empty publication")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "all_financing_stage_gem_evidence.csv"
    json_path = args.output_dir / "full_coverage_audit_summary.json"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
