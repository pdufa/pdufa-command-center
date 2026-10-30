"""CLI entrypoint for opt-in nightly PREDICTIONS research hook.

Example (research only):
 python -m research.predictions_nightly_cli --candidates /path/candidates.json \
   --evidence /path/evidence.json --jobs /path/jobs --enable

Input candidate records must come from real scan exports. The evidence JSON
maps trial IDs to assessment titles and sourced findings. No scan is launched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.predictions_nightly_hook import after_nightly_scan


def run_cli(argv=None) -> dict:
    parser = argparse.ArgumentParser(description="Research-only PREDICTIONS nightly hook")
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--enable", action="store_true")
    args = parser.parse_args(argv)
    if not args.enable:
        return {"status": "DISABLED", "reason": "Explicit --enable required"}
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    if not isinstance(candidates, list) or not isinstance(evidence, dict):
        raise ValueError("Expected candidate list and evidence mapping")
    if not all(isinstance(row, dict) for row in candidates):
        raise ValueError("Each candidate must be an object")
    return after_nightly_scan(
        args.jobs, candidates, lambda trial_id: evidence.get(trial_id, {}),
        enabled=True,
    )


def main() -> None:
    print(json.dumps(run_cli(), sort_keys=True))


if __name__ == "__main__":
    main()
