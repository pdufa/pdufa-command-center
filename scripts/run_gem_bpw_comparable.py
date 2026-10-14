#!/usr/bin/env python3
"""Run GEM coverage comparison against BPW publicly described feature set.

This does not access BiopharmaWatch's private API and cannot assert equal
accuracy, equal coverage or comparable proprietary approval probabilities.
"""
from __future__ import annotations
import argparse
import csv
import io
import json
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gem_bpw_comparable import build_comparable  # noqa: E402
from gem_scans import build_gem_scans  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "reports/gem_daily")
    parser.add_argument("--as-of", type=str)
    args = parser.parse_args(argv)
    asof = date.fromisoformat(args.as_of) if args.as_of else datetime.now(
        ZoneInfo("America/Los_Angeles")).date()
    rows, _ = build_gem_scans(args.data_dir, as_of=asof)
    try:
        source = json.loads((args.data_dir/"gem_hedge_fund_13f.json").read_text(encoding="utf-8"))
        if source.get("source") != "SEC_13F_XML_INFO_TABLE":
            source = {}
    except (OSError, ValueError, TypeError):
        source = {}
    report = build_comparable(args.data_dir, rows, as_of=asof, hedge_report=source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.data_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        args.data_dir/"gem_bpw_comparable.json":
            json.dumps(report, indent=2, sort_keys=True)+"\n",
        args.output_dir/"gem_bpw_comparable.json":
            json.dumps(report, indent=2, sort_keys=True)+"\n",
    }
    for path, value in outputs.items():
        temp = path.with_name(path.name+".tmp")
        temp.write_text(value, encoding="utf-8")
        temp.replace(path)
    matrix = report["capability_matrix"]
    with (args.output_dir/"gem_bpw_comparable_matrix.csv").open(
            "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(matrix[0]) if matrix else ["key"])
        writer.writeheader()
        writer.writerows(matrix)
    # Emit a real UTF-8 CSV with an explicit schema even for zero candidates.
    columns = ("Ticker", "Drug", "Exact event", "Entry benchmark 1 verified",
               "Entry benchmark 2 verified", "GEM priority rank", "GEM priority score /100",
               "Phase 3 quality", "Cash runway months", "Hedge-fund managers holding",
               "Hedge-fund managers adding", "Market capitalization USD",
               "PDUFA date", "Insider open-market purchases",
               "Insider purchase amount USD", "Insider source links",
               "Risk flags", "BPW PoA score",
               "BPW approval/outperformance similarity")
    with (args.output_dir/"gem_bpw_two_benchmark_candidates.csv").open(
            "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(report["ranked_two_benchmark_candidates"])
    print(json.dumps({
        "as_of_pacific": asof.isoformat(),
        "gem_program_rows": report["gem_observed_program_rows"],
        "gem_eligible_candidates": report["gem_two_benchmark_eligible"],
        "feature_coverage_report": str(args.data_dir/"gem_bpw_comparable.json"),
        "bpw_direct_scores": "NOT AVAILABLE",
        "returns_validated": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
