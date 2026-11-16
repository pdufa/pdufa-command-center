"""Offline SHA256 integrity checks for historical primary-source document bytes.

A source record's SHA256 string alone is not proof of document integrity.
Actual bytes must be supplied independently. No network or file writes.
"""
from __future__ import annotations

import hashlib
from typing import Any


def verify_historical_source_bytes(
    source_records: list[dict[str, Any]], artifacts: list[dict[str, Any]]
) -> dict[str, Any]:
    if not isinstance(source_records, list) or not isinstance(artifacts, list):
        raise TypeError("Source records and artifacts must be lists")
    errors: list[str] = []
    indexed: dict[str, bytes] = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"ARTIFACT_{index}_INVALID")
            continue
        url = artifact.get("source_url")
        data = artifact.get("content_bytes")
        if not isinstance(url, str) or not url:
            errors.append(f"ARTIFACT_{index}_MISSING_URL")
            continue
        if url in indexed:
            errors.append(f"ARTIFACT_{index}_DUPLICATE_URL")
            continue
        if not isinstance(data, bytes):
            errors.append(f"ARTIFACT_{index}_MISSING_BYTES")
            continue
        indexed[url] = data
    seen: set[str] = set()
    verified = 0
    for index, record in enumerate(source_records):
        if not isinstance(record, dict):
            errors.append(f"SOURCE_{index}_INVALID")
            continue
        url = record.get("source_url")
        digest = record.get("sha256")
        if not isinstance(url, str) or not url:
            errors.append(f"SOURCE_{index}_MISSING_URL")
            continue
        if url in seen:
            errors.append(f"SOURCE_{index}_DUPLICATE_URL")
        seen.add(url)
        if url not in indexed:
            errors.append(f"SOURCE_{index}_MISSING_ARTIFACT")
            continue
        if not isinstance(digest, str) or len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest.lower()
        ):
            errors.append(f"SOURCE_{index}_INVALID_SHA256")
            continue
        if hashlib.sha256(indexed[url]).hexdigest() != digest.lower():
            errors.append(f"SOURCE_{index}_HASH_MISMATCH")
            continue
        verified += 1
    for url in indexed:
        if url not in seen:
            errors.append("UNLINKED_ARTIFACT")
    return {
        "source_count": len(source_records),
        "verified_source_byte_count": verified,
        "source_bytes_verified": bool(source_records) and not errors and
        verified == len(source_records),
        "blind_eligible": False,
        "accuracy_evaluated": False,
        "errors": errors,
    }
