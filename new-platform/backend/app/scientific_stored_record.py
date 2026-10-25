"""Read-only, bounded and checksum-verified ClinicalTrials.gov archive access.

Registry metadata is descriptive and must never be converted directly into
verified clinical efficacy, safety or FDA-approval scores.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import re

from .scientific_registry_evidence import extract_trial_evidence

# ClinicalTrials.gov API responses are capped at 10 MB at ingestion. Allow
# canonical JSON expansion while rejecting unexpectedly large decompression.
MAX_ARCHIVED_JSON_BYTES = 20_000_000
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")


def verified_record_from_archive(nct_id: str, payload_gzip: bytes,
                                 expected_sha256: str) -> dict:
    """Validate archive size, checksum, JSON shape and exact trial identity."""
    if not isinstance(payload_gzip, bytes):
        raise ValueError("Archived payload must be bytes")
    if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(expected_sha256):
        raise ValueError("Archived checksum must be a SHA-256 hex digest")
    # Bounded read prevents gzip bombs before checksum/identity validation.
    with gzip.GzipFile(fileobj=io.BytesIO(payload_gzip), mode="rb") as archive:
        raw = archive.read(MAX_ARCHIVED_JSON_BYTES + 1)
    if len(raw) > MAX_ARCHIVED_JSON_BYTES:
        raise ValueError("Archived record exceeds expanded size limit")
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Archived record checksum mismatch")
    record = json.loads(raw)
    if not isinstance(record, dict):
        raise ValueError("Archived trial record must be an object")
    extract_trial_evidence(nct_id, record)
    return record


def evidence_from_archive(nct_id: str, payload_gzip: bytes,
                          expected_sha256: str) -> dict:
    record = verified_record_from_archive(nct_id, payload_gzip, expected_sha256)
    return extract_trial_evidence(nct_id, record)
