"""Read-only integrity and identity verification of archived ClinicalTrials.gov data.

A registry record is descriptive source evidence only; passing this check
cannot establish clinical efficacy, safety, or an FDA approval probability.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re

from .scientific_registry_evidence import extract_trial_evidence

# Registry API responses are capped at 10 MB before canonical JSON encoding.
# Allow canonicalization overhead but reject unexpectedly large archives.
MAX_ARCHIVED_JSON_BYTES = 20_000_000
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\\Z")


def evidence_from_archive(nct_id: str, payload_gzip: bytes, expected_sha256: str) -> dict:
    if not isinstance(payload_gzip, bytes):
        raise ValueError("Archived payload must be bytes")
    if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("Archived checksum must be a SHA-256 hex digest")

    # Bounded streaming extraction prevents corrupted or hostile gzip content
    # from exhausting memory before checksum and identity validation.
    with gzip.GzipFile(fileobj=io.BytesIO(payload_gzip), mode="rb") as archive:
        raw = archive.read(MAX_ARCHIVED_JSON_BYTES + 1)
    if len(raw) > MAX_ARCHIVED_JSON_BYTES:
        raise ValueError("Archived record exceeds expanded size limit")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Archived record checksum mismatch")
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("Archived trial record must be an object")
    return extract_trial_evidence(nct_id, record)
