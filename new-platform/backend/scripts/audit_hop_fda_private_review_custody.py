"""Private only: create or check a frozen BLANK FDA A/B source baseline.

Does not store files beyond the provided private directory, encrypt them,
authenticate reviewers, adjudicate regulatory decisions, or train predictions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.hop_fda_private_review_custody import (
    save_private_blank_batch_manifest, verify_private_blank_batch_manifest,
)

REPOSITORY = Path(__file__).resolve().parents[3]


def main() -> int:
    p = argparse.ArgumentParser(description="Private FDA A/B batch checksum integrity")
    p.add_argument("--private-batch-dir", type=Path, required=True)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--create-baseline", action="store_true")
    mode.add_argument("--verify-baseline", action="store_true")
    args = p.parse_args()
    folder = args.private_batch_dir.resolve()
    if folder == REPOSITORY or folder.is_relative_to(REPOSITORY):
        raise ValueError("Private FDA source/manifest cannot be inside the repository")
    if "public_aggregate_only" in folder.parts:
        raise ValueError("FDA custody manifests belong only in private source storage")
    if args.create_baseline:
        results = save_private_blank_batch_manifest(folder)
        # Public stdout is numerical confirmation only; not private SHA data.
        print(json.dumps({
            "status": "PRIVATE_BLANK_FDA_BASELINE_PREPARED_NOT_ADJUDICATED",
            "batch_count": results["batch_count"],
            "private_role_files_counted": results["file_count"],
            "original_fda_review_cycles_verified": 0,
            "model_eligible_records": 0,
            "prediction_probability": None,
        }, sort_keys=True))
    else:
        print(json.dumps(verify_private_blank_batch_manifest(folder), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
