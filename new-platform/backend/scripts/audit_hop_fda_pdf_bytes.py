#!/usr/bin/env python3
"""Compute real original FDA PDF byte provenance, WITHOUT certifying outcomes.

Usage:
  PYTHONPATH=new-platform/backend python new-platform/backend/scripts/audit_hop_fda_pdf_bytes.py \
    NDA213973_ORIGINAL_1_20200515_APPROVED /path/to/downloaded-letter.pdf

The caller obtains the PDF independently from the exact official URL printed
in the versioned research manifest. This script does not fetch, upload, store,
or publish copyrighted PDFs. It never claims a successful scientific review.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from app.hop_primary_action_letter_samples import _SAMPLE_FILE, _url_ok

MAX_PDF_BYTES = 50 * 1024 * 1024
MIN_PDF_BYTES = 1024


def inspect_local_pdf(data: bytes) -> dict:
    """Untrusted local file signature and hash, not authentication of publisher."""
    if not isinstance(data, bytes) or not MIN_PDF_BYTES <= len(data) <= MAX_PDF_BYTES:
        raise ValueError("PDF source outside bounded byte size")
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise ValueError("Input has no recognizable PDF header/end marker")
    return {
        "status": "BYTES_HASHED_NEEDS_IDENTITY_AND_CHRONOLOGY_REVIEW",
        "byteLength": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "originalLetterIndependentlyAdjudicated": False,
        "originalPublicationDateVerified": False,
        "modelEligible": False,
        "approvalProbability": None,
    }


def audit_file(record_id: str, pdf: Path) -> dict:
    manifest = json.loads(_SAMPLE_FILE.read_text(encoding="utf-8"))
    candidates = [r for r in manifest["letters"] if r["record_id"] == record_id]
    if len(candidates) != 1:
        raise ValueError("Unknown or nonunique exact FDA source record")
    record = candidates[0]
    if not _url_ok(record["original_document_url"]):
        raise ValueError("Not an exact official FDA source URL")
    if not pdf.is_file() or pdf.is_symlink():
        raise ValueError("Expected a regular locally supplied PDF")
    with pdf.open("rb") as f:
        content = f.read(MAX_PDF_BYTES + 1)
    digest = inspect_local_pdf(content)
    return {
        "recordId": record_id,
        "expectedOfficialUrl": record["original_document_url"],
        "sourceFileClaimsOfficialOrigin": False,
        "downloadOriginProvenByByteHash": False,
        **digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record_id")
    parser.add_argument("local_pdf")
    args = parser.parse_args()
    try:
        report = audit_file(args.record_id, Path(args.local_pdf))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"FDA PDF audit blocked: {exc}\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
