#!/usr/bin/env python3
"""Controlled source-bound HTTPS capture of original public FDA PDF bytes.

Only the two exact FDA PDF URLs already inspected and committed in the
historical source manifest can be requested. This tool does not train a model,
infer document publication date, or certify the contents' review-cycle truth.

Use on a reviewed, unprivileged runner with no API keys. Its output is a
short-retention local evidence folder, never a Git commit or database write.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.error import HTTPError
from urllib.request import (
    HTTPRedirectHandler, Request, build_opener,
)

from app.hop_primary_action_letter_samples import _SAMPLE_FILE, _url_ok

MAX_BYTES = 20 * 1024 * 1024
MIN_BYTES = 1024
CHUNK_SIZE = 128 * 1024
_SAFE_KEY = re.compile(r"(?:NDA|BLA)\d{6}_ORIGINAL_[1-9]\d*_\d{8}_(?:APPROVED|CRL)\Z")


class NoRedirects(HTTPRedirectHandler):
    """A source host silently redirecting elsewhere is NOT same-source proof."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("External redirect blocked: original FDA URL changed")


def _source_record(manifest: dict, record_id: str) -> dict:
    if not isinstance(record_id, str) or not _SAFE_KEY.fullmatch(record_id):
        raise ValueError("Malformed exact FDA action record identity")
    matches = [r for r in manifest.get("letters", []) if r.get("record_id") == record_id]
    if len(matches) != 1:
        raise ValueError("Only one previously curated exact FDA letter ID may be fetched")
    row = matches[0]
    if (not _url_ok(row.get("original_document_url"))
            or row.get("eligible_for_training") is not False
            or row.get("source_document_bytes_sha256") is not None):
        raise ValueError("Expected immutable official FDA URL and unadjudicated source status")
    return row


def capture_fda_pdf_bytes(
    manifest: dict, record_id: str, output_directory: Path, *,
    opener=None, observed_at: datetime | None = None,
) -> dict:
    """Stream bounded source bytes and only then atomically retain them.

    Successful HTTPS retrieval authenticates the connection to the permitted
    FDA hostname, not the signed FDA action, first publication, or scientific
    truth of the PDF. No arbitrary URLs, custom certificates or auth headers.
    """
    row = _source_record(manifest, record_id)
    output_directory = Path(output_directory)
    if output_directory.is_symlink():
        raise ValueError("Evidence output directory may not be a symlink")
    if not output_directory.is_dir():
        raise ValueError("Evidence output directory must already exist")
    target_pdf = output_directory / f"{record_id}.pdf"
    target_json = output_directory / f"{record_id}.provenance.json"
    if target_pdf.exists() or target_json.exists():
        raise ValueError("Refusing to overwrite an existing source capture")
    if observed_at is None:
        observed_at = datetime.now(timezone.utc)
    if (not isinstance(observed_at, datetime)
            or observed_at.tzinfo is None or observed_at.utcoffset() is None):
        raise ValueError("Capture timestamp must be timezone-aware")
    url = row["original_document_url"]
    operation = opener or build_opener(NoRedirects())
    request = Request(url, headers={
        "Accept": "application/pdf",
        "User-Agent": "PDUFA-Research-Source-Audit/1.0",
    }, method="GET")
    path = None
    total = 0
    digest = hashlib.sha256()
    head = b""
    tail = b""
    response_headers = {}
    try:
        with closing(operation.open(request, timeout=30)) as response:
            status = getattr(response, "status", None)
            if status != 200 or response.geturl() != url:
                raise ValueError("Original FDA HTTPS response is not exact-url HTTP 200")
            media = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
            if media and media not in {"application/pdf", "application/octet-stream"}:
                raise ValueError("Official FDA response is not a PDF media type")
            response_headers = {
                "contentType": media or None,
                "httpLastModifiedHeader": response.headers.get("Last-Modified"),
                "httpDateHeader": response.headers.get("Date"),
                "httpETag": response.headers.get("ETag"),
            }
            fd, path = tempfile.mkstemp(prefix=".fda-pdf-", suffix=".tmp", dir=output_directory)
            with os.fdopen(fd, "wb") as out:
                while True:
                    part = response.read(CHUNK_SIZE)
                    if not part:
                        break
                    if not isinstance(part, bytes):
                        raise ValueError("Unexpected nonbinary FDA document response")
                    total += len(part)
                    if total > MAX_BYTES:
                        raise ValueError("FDA source exceeds 20 MiB maximum")
                    head = (head + part)[:8]
                    tail = (tail + part)[-2048:]
                    digest.update(part)
                    out.write(part)
                out.flush()
                os.fsync(out.fileno())
        if total < MIN_BYTES or not head.startswith(b"%PDF-") or b"%%EOF" not in tail:
            raise ValueError("FDA response lacks bounded PDF header, EOF or minimum size")
        # The successful network read is not an independent content review.
        result = {
            "schemaVersion": "hop-fda-original-https-byte-capture-v1",
            "recordId": record_id,
            "exactRequestedFdaUrl": url,
            "httpStatus": 200,
            "redirected": False,
            "observedAtUtc": observed_at.astimezone(timezone.utc).isoformat(timespec="seconds"),
            **response_headers,
            "originalResponseBytesCaptured": True,
            "byteLength": total,
            "sha256OfCapturedBytes": digest.hexdigest(),
            "sourcePublisherConnection": "HTTPS_TLS_TO_ALLOWLISTED_FDA_HOST",
            "sourceDocumentIndependentlyReviewed": False,
            "documentReferenceAndActionIndependentlyAdjudicated": False,
            "FDAletterFirstPublishedAt": None,
            "historicalReviewCycleVerified": False,
            "frozenPredecisionFeaturesVerified": False,
            "modelEligible": False,
            "approvalProbability": None,
            "archiveRetention": "SHORT_LIVED_RESTRICTED_CI_ARTIFACT",
        }
        # Materialize the PDF only after all checks; never append or overwrite.
        os.link(path, target_pdf)
        with target_json.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")
        return result
    finally:
        if path is not None:
            Path(path).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", help="Pre-created local ephemeral evidence folder")
    parser.add_argument("--record-id", choices=[
        "NDA213973_ORIGINAL_1_20200515_APPROVED",
        "BLA761303_ORIGINAL_1_20240322_CRL",
    ], action="append", dest="ids")
    args = parser.parse_args()
    original = json.loads(_SAMPLE_FILE.read_text(encoding="utf-8"))
    ids = args.ids or [r["record_id"] for r in original["letters"]]
    audit = {
        "schemaVersion": "hop-fda-original-https-capture-batch-v1",
        "status": "SOURCE_CAPTURE_NOT_COMPLETED",
        "captured": [],
        "failures": [],
        "trainingAuthorized": False,
        "historicalModelEligibleRecords": 0,
        "approvalProbability": None,
    }
    for record_id in ids:
        try:
            audit["captured"].append(capture_fda_pdf_bytes(
                original, record_id, Path(args.output_directory),
            ))
        except (OSError, ValueError, HTTPError) as exc:
            audit["failures"].append({"recordId": record_id, "reason": type(exc).__name__})
    audit["status"] = (
        "BYTES_CAPTURED_REVIEW_STILL_REQUIRED" if audit["captured"] and not audit["failures"]
        else "SOURCE_CAPTURE_PARTIAL_OR_BLOCKED"
    )
    print(json.dumps(audit, indent=2))
    return 0 if not audit["failures"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
