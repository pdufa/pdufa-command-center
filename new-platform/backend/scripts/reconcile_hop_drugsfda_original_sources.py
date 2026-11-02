"""Compare pinned actual FDA Drugs@FDA table snapshot to saved openFDA JSON.

This cross-source operation is *research only*: no FDA outcome verification,
no model training, and no change to live GEM JR/GEM/WT functionality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path

from app.hop_drugsfda_original_source_diff import reconcile_original_submission_sources
from app.hop_drugsfda_submission_spine import audit_original_submissions


SOURCE_DIR = Path(__file__).resolve().parents[1] / "app" / "research_sources"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pinned FDA original NDA/BLA submission membership discrepancy audit"
    )
    parser.add_argument("--applications", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--saved-openfda-registry-json", type=Path, required=True)
    parser.add_argument("--as-of", required=True, type=date.fromisoformat)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()
    index_tab = json.loads((SOURCE_DIR /
        "hop_drugsfda_original_submissions_20261025.json"
    ).read_text(encoding="utf-8"))
    index_arch = json.loads((SOURCE_DIR /
        "hop_drugsfda_original_submissions_artifact_index.json"
    ).read_text(encoding="utf-8"))
    original_bytes = args.saved_openfda_registry_json.read_bytes()
    digest = hashlib.sha256(original_bytes).hexdigest()
    if digest != index_arch.get("github_artifact_json_sha256"):
        raise ValueError("Pinned saved openFDA archive JSON digest does not match")
    raw_archived = json.loads(original_bytes)
    tabular = audit_original_submissions(
        args.applications, args.submissions, as_of=args.as_of
    )
    report = reconcile_original_submission_sources(
        tabular, raw_archived, tabular_index=index_tab,
        archive_index=index_arch, as_of=args.as_of,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    # This means only SOURCE MEMBERSHIP was compared; never scientific success.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
