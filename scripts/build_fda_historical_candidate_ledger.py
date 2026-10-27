"""Build a quarantined FDA historical candidate ledger (research only).

Reads local JSON candidate files, screens metadata, and emits a deterministic
report to stdout. Never writes source records or upgrades verification status.
Usage: python scripts/build_fda_historical_candidate_ledger.py data/fda_candidate_*.json
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

try:
    from .screen_fda_evidence import screen_candidate
except ImportError:  # direct script execution
    from screen_fda_evidence import screen_candidate


def build_ledger(rows):
    results = []
    seen = {}
    for row in rows:
        screening = screen_candidate(row)
        key = (row.get("application_id"), row.get("submission_id"), row.get("review_cycle")) if isinstance(row, dict) else (None, None, None)
        issues = list(screening["issues"])
        if key in seen:
            issues.append("duplicate_review_cycle_requires_adjudication")
            results[seen[key]]["issues"].append("duplicate_review_cycle_requires_adjudication")
            results[seen[key]]["status"] = "QUARANTINED"
        else:
            seen[key] = len(results)
        results.append({
            "application_id": row.get("application_id") if isinstance(row, dict) else None,
            "submission_id": row.get("submission_id") if isinstance(row, dict) else None,
            "review_cycle": row.get("review_cycle") if isinstance(row, dict) else None,
            "action_type": row.get("action_type") if isinstance(row, dict) else None,
            "status": "QUARANTINED" if issues else "CANDIDATE_METADATA_COMPLETE",
            "issues": issues,
            "independently_verified": False,
            "model_eligible": False,
        })
    return {
        "input_candidates": len(results),
        "status_counts": dict(sorted(Counter(r["status"] for r in results).items())),
        "independently_verified_pass": 0,
        "independently_verified_fail": 0,
        "model_eligible": 0,
        "candidate_review_cycles": results,
        "warning": "Metadata and source links do not verify FDA documents, independent adjudication, or model readiness.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        rows = [json.loads(path.read_text(encoding="utf-8")) for path in args.files]
        print(json.dumps(build_ledger(rows), indent=2, sort_keys=True))
    except (OSError, ValueError, TypeError) as exc:
        print(f"LEDGER_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
