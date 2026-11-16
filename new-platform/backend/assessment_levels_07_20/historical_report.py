"""Offline, read-only JSON report for isolated historical PDUFA cohort preparation.

Usage:
  PYTHONPATH=new-platform/backend python -m assessment_levels_07_20.historical_report \
      --manifest path/to/manifest.json --evidence path/to/evidence.json

No network calls, data mutations, FDA outcome access, or prediction generation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .historical_coverage import summarize_historical_coverage


def _read_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline blind historical evidence coverage report")
    parser.add_argument("--manifest", required=True, help="Local frozen cohort manifest JSON")
    parser.add_argument("--evidence", required=True, help="Local pre-cutoff evidence JSON list")
    args = parser.parse_args(argv)
    try:
        manifest = _read_json(args.manifest)
        evidence = _read_json(args.evidence)
        report = summarize_historical_coverage(manifest, evidence)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Historical preflight input error: {type(error).__name__}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["eligible_for_blind_review"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
