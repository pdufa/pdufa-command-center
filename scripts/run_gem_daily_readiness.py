#!/usr/bin/env python3
"""Write dated research-only GEM observations and source-readiness audit.

Archive output as GitHub Actions artifacts. This script intentionally does
not visit any website, assert live source coverage, change scores, or trade.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gem_scans import build_gem_scans  # noqa: E402
from gem_phase3_discovery import discover_phase3_results  # noqa: E402
from gem_readiness_audit import build_readiness_report  # noqa: E402
from gem_prospective import build_observations, observations_csv  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/gem_daily")
    parser.add_argument("--as-of", type=str,
                        help="Pacific research observation date YYYY-MM-DD")
    args = parser.parse_args(argv)
    from datetime import date
    asof = (date.fromisoformat(args.as_of) if args.as_of else
            datetime.now(ZoneInfo("America/Los_Angeles")).date())
    try:
        scans, scan_status = build_gem_scans(args.data_dir, as_of=asof)
        discovered, discovery_status = discover_phase3_results(args.data_dir, as_of=asof)
        report = build_readiness_report(
            args.data_dir, scans, scan_status, discovered, discovery_status, as_of=asof
        )
        observations = build_observations(scans, scan_status, as_of=asof)
    except (OSError, ValueError, TypeError, KeyError) as err:
        parser.error("GEM audit failed closed: " + str(err))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Each run stores its own UTC timestamp for artifact retention; do not
    # present the report as a verified historical returns dataset.
    (args.output_dir / "gem_readiness.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (args.output_dir / "gem_prospective_research_only.csv").write_text(
        observations_csv(observations), encoding="utf-8")
    print(json.dumps({
        "research_status": report["research_status"],
        "full_universe_coverage_verified": False,
        "historical_return_edge_validated": False,
        "saved_source_records": report["saved_pipeline_events"],
        "prospective_research_observations": len(observations),
        "output_directory": str(args.output_dir),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
