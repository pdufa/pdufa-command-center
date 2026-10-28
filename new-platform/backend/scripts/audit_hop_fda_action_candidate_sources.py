#!/usr/bin/env python3
"""Reconstruct FDA action-source candidates from two pinned archival exports.

Usage (offline):
  PYTHONPATH=new-platform/backend python \
    new-platform/backend/scripts/audit_hop_fda_action_candidate_sources.py \
    --approved-artifact /path/to/drugsfda_artifact.zip \
    --crl-artifact /path/to/crl_artifact.zip \
    --output-directory /path/to/precreated/empty/output

Neither the research candidate queue nor its counts is an unbiased FDA
decision cohort, a PDUFA filing-year roster, or a source of model labels.
"""
from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import zipfile

from app.hop_fda_action_candidate_universe import build_fda_action_candidate_queue

_APP_CONTENT = "drugsfda_approved_registry_quarantined.json"
_CRL_CONTENT = "fda_crl_published_quarantined.json"
_APP_SHA256 = "adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2"
_CRL_SHA256 = "d3d284e1ec0aa62b6dfb7523bd7bbfc7324c3b218a412fd6ee357a35f5c39898"
_MAX_BYTES = 100 * 1024 * 1024
_BENCHMARK = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
              / "hop_fda_pdufa_filing_benchmarks.json")


def _quarantined_json(artifact_zip: Path, *, name: str, expected_sha256: str) -> dict:
    """Extract exactly the pinned archive member; no arbitrary ZIP paths."""
    if not artifact_zip.is_file() or artifact_zip.is_symlink():
        raise ValueError("An existing regular GitHub evidence ZIP is required")
    with zipfile.ZipFile(artifact_zip) as z:
        matches = [x for x in z.infolist() if x.filename == name]
        if len(matches) != 1 or matches[0].file_size > _MAX_BYTES:
            raise ValueError("Required archived FDA source snapshot is missing or oversized")
        source = z.read(matches[0])
    if hashlib.sha256(source).hexdigest() != expected_sha256:
        raise ValueError("FDA archived source snapshot hash does not match pinned research evidence")
    document = json.loads(source)
    if not isinstance(document, dict):
        raise ValueError("FDA archive content must be a single source object")
    return document


def run(approved_artifact: Path, crl_artifact: Path, *, as_of: date) -> dict:
    approval = _quarantined_json(
        approved_artifact, name=_APP_CONTENT, expected_sha256=_APP_SHA256)
    crl = _quarantined_json(
        crl_artifact, name=_CRL_CONTENT, expected_sha256=_CRL_SHA256)
    benchmarks = json.loads(_BENCHMARK.read_text(encoding="utf-8"))
    result = build_fda_action_candidate_queue(
        approval, crl, benchmarks, as_of=as_of)
    result["researchSourceProvenance"] = {
        "approvedProductRegistry": {
            "sourceSnapshotSha256": _APP_SHA256,
            "sourceArtifactId": 12611090768,
            "sourceArtifactUrl": "https://github.com/pdufa/pdufa-command-center/actions/runs/40224730350/artifacts/12611090768",
            "asPublishedExportDate": approval["source_export_date"],
            "sourceStatus": "APPROVAL_SELECTED_ARCHIVE",
        },
        "selectedPublishedCRLs": {
            "sourceSnapshotSha256": _CRL_SHA256,
            "sourceArtifactId": 12610736354,
            "sourceArtifactUrl": "https://github.com/pdufa/pdufa-command-center/actions/runs/40224038609/artifacts/12610736354",
            "asPublishedExportDate": crl["source_export_date"],
            "sourceStatus": "PUBLICATION_SELECTED_ARCHIVE",
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-artifact", required=True)
    parser.add_argument("--crl-artifact", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--as-of", default="2026-10-28")
    args = parser.parse_args()
    cutoff = date.fromisoformat(args.as_of)
    out = Path(args.output_directory)
    if not out.is_dir() or out.is_symlink():
        parser.error("Output directory must already exist and must not be a symlink")
    full = out / "hop_fda_source_candidate_queue_research_only.json"
    summary = out / "hop_fda_source_candidate_audit_research_only.json"
    if full.exists() or summary.exists():
        parser.error("Refusing to overwrite existing candidate audit evidence")
    result = run(
        Path(args.approved_artifact), Path(args.crl_artifact), as_of=cutoff)
    candidates = result.pop("researchCandidates")
    # Both writes are research artifacts; no database, production sheet,
    # scientific reviewer register, trade or independent model training.
    result["researchCandidateFile"] = full.name
    result["researchCandidateFileSha256"] = hashlib.sha256(
        (json.dumps(candidates, indent=2, sort_keys=True) + "\n").encode()
    ).hexdigest()
    with full.open("x", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2, sort_keys=True)
        f.write("\n")
    with summary.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
