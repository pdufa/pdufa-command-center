#!/usr/bin/env python3
"""Save the first date each exact Pipeline trial appears in GEM JR / GEM.

Run after the relevant collector and evidence validation. No stage/date backfill,
no promotion of research leads, and no use of financial-event dates as discoveries.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gem_stage_history import observe
from pipeline_source_scope import pipeline_origins
from gem_potential_list import build_potential_list
from gem_scans import build_gem_scans


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=("GEM_JR", "GEM"))
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    args = parser.parse_args(argv)
    pacific_day = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    canonical, companies = pipeline_origins(args.data_dir, today=pacific_day)
    if not canonical:
        raise SystemExit("No canonical Pipeline records — declining to create discovery timestamps")
    if args.stage == "GEM_JR":
        active, held = build_potential_list(args.data_dir, as_of=pacific_day)
        stage_rows = active + held
    else:
        stage_rows, status = build_gem_scans(args.data_dir, as_of=pacific_day)
        if not status.get("feed_current") or not status.get("sec_financing_source_current"):
            raise SystemExit("GEM source verification stale/partial: stage dates not recorded")
    # Identity checks are per ID and per ticker, not generic stock-symbol joins.
    records = []
    for row in stage_rows:
        pid = str(row.get("Pipeline ID") or "")
        ticker = str(row.get("Ticker") or "").strip().upper()
        if pid in canonical and companies.get(pid) == ticker:
            records.append(row)
    result = observe(args.data_dir, args.stage, records, observed_on=pacific_day,
                     validated_pipeline_ids=canonical)
    print(json.dumps({"stage": args.stage, "date_pacific": pacific_day.isoformat(),
                      "pipeline_matched": len(records), **result}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
