"""Offline CLI for Pipeline research snapshots; no production access or writes.

Usage:
  python -m research.preliminary_pipeline_snapshot_cli input.json output.json
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from research.preliminary_pipeline_snapshot import triage_pipeline_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    if args.input.resolve() == args.output.resolve():
        parser.error("input and output paths must differ")
    if args.input.stat().st_size > 10_000_000:
        parser.error("snapshot exceeds 10MB")
    with args.input.open("r", encoding="utf-8") as source:
        snapshot = json.load(source)
    report = triage_pipeline_snapshot(
        snapshot, now=datetime.now(timezone.utc).isoformat())
    # No write occurs unless the full snapshot validates.
    if args.output.exists():
        parser.error("output already exists; refusing overwrite")
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(report, target, indent=2, sort_keys=True, allow_nan=False)
        target.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
