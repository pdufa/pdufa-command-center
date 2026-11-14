#!/usr/bin/env python3
"""Offline local-byte consistency receipts for Level 1–6 evidence submissions.

Matching a local file to a user-provided SHA-256 proves ONLY local byte
consistency. It does not authenticate the publication, source URL, original
acquisition, document meaning, reviewer, or scientific conclusion.
No network access, file modifications, or database writes are performed.
"""
from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
import re

MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_RECORDS = 2000
SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _path(root, value):
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError("Receipt path must be a bounded relative POSIX path")
    path = PurePosixPath(value)
    parts = value.split("/")
    if (path.is_absolute() or value != path.as_posix()
            or any(part in {"", ".", ".."} or not SEGMENT.fullmatch(part)
                   for part in parts)):
        raise ValueError("Receipt path must remain inside the local evidence root")
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("Symlinked evidence paths are not permitted")
    if not current.resolve(strict=False).is_relative_to(root):
        raise ValueError("Receipt path escapes the local evidence root")
    return current


def _digest(path):
    """Hash bounded file bytes; never emit the document text in the receipt."""
    if not path.exists():
        return {"byteMatchStatus": "LOCAL_FILE_NOT_PRESENT", "bytesRead": 0,
                "computedSha256": None}
    if not path.is_file():
        raise ValueError("Receipt path must be a regular file")
    if path.stat().st_size > MAX_SOURCE_BYTES:
        raise ValueError("Receipt file is larger than the 64 MiB intake limit")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            count += len(chunk)
            if count > MAX_SOURCE_BYTES:
                raise ValueError("Receipt source exceeded the 64 MiB intake limit")
            digest.update(chunk)
    return {"byteMatchStatus": "LOCAL_BYTES_READ", "bytesRead": count,
            "computedSha256": digest.hexdigest()}


def match_local_bytes(submissions_by_nct, receipt_manifest, evidence_root):
    """Return per-submission statuses; NO independent verification promotion.

    The manifest cannot assert review/verification. Every manifest row must
    match an already-validated exact-NCT source submission ID.
    """
    if not isinstance(submissions_by_nct, dict):
        raise ValueError("Expected validated evidence submissions")
    if not isinstance(receipt_manifest, dict) or set(receipt_manifest) != {
        "schemaVersion", "kind", "records"
    } or receipt_manifest.get("schemaVersion") != 1 or receipt_manifest.get(
        "kind"
    ) != "FOCUS_LEVELS_1_6_LOCAL_BYTE_RECEIPTS":
        raise ValueError("Invalid local receipt manifest schema")
    rows = receipt_manifest.get("records")
    if not isinstance(rows, list) or len(rows) > MAX_RECORDS:
        raise ValueError("Invalid local receipt manifest records")
    root = Path(evidence_root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Local evidence root must be an existing ordinary directory")
    root = root.resolve(strict=True)
    known = {}
    for nct, source_rows in submissions_by_nct.items():
        if not isinstance(source_rows, list):
            raise ValueError("Invalid validated submission rows")
        for source in source_rows:
            submission_id = source["submissionId"]
            if submission_id in known:
                raise ValueError("Duplicate source submission in the validated queue")
            known[submission_id] = (nct, source["submittedDigestUnverified"])

    receipts = {}
    for entry in rows:
        if not isinstance(entry, dict) or set(entry) != {"submissionId", "relativePath"}:
            raise ValueError("Local receipt row must contain ID and relative path only")
        ident = entry["submissionId"]
        if not isinstance(ident, str) or ident not in known or ident in receipts:
            raise ValueError("Unknown or duplicate local receipt ID")
        path = _path(root, entry["relativePath"])
        result = _digest(path)
        if result["byteMatchStatus"] == "LOCAL_BYTES_READ":
            result["byteMatchStatus"] = (
                "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY"
                if result["computedSha256"] == known[ident][1]
                else "LOCAL_DIGEST_MISMATCH"
            )
        receipts[ident] = result

    matched = sum(x["byteMatchStatus"] == "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY"
                  for x in receipts.values())
    mismatched = sum(x["byteMatchStatus"] == "LOCAL_DIGEST_MISMATCH"
                     for x in receipts.values())
    missing = sum(x["byteMatchStatus"] == "LOCAL_FILE_NOT_PRESENT"
                  for x in receipts.values())
    return {
        "receipts": receipts,
        "summary": {
            "sourceSubmissionCount": len(known),
            "receiptEntries": len(receipts),
            "localByteMatches": matched,
            "localDigestMismatches": mismatched,
            "localFilesNotPresent": missing,
            "sourcesWithoutLocalReceipt": len(known) - len(receipts),
            "originalSourceAuthenticated": 0,
            "independentScientificReviews": 0,
            "status": "LOCAL_BYTE_CONSISTENCY_ONLY_NOT_SOURCE_AUTHENTICATION",
        },
    }
