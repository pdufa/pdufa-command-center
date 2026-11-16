"""Offline byte hashing for historical research downloads.

This helper records today's supplied retrieval timestamp, not a historical
retrieval claim. The resulting manifest is discovery-only and cannot be
submitted as pre-decision frozen evidence.
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any


def package_discovery_source_bytes(
    source_url: str, content_bytes: bytes, retrieved_at: str
) -> dict[str, Any]:
    if not isinstance(source_url, str) or not source_url.startswith("https://"):
        raise ValueError("Source URL must use HTTPS")
    if not isinstance(content_bytes, bytes) or not content_bytes:
        raise ValueError("Nonempty source bytes are required")
    if not isinstance(retrieved_at, str):
        raise ValueError("Explicit retrieval timestamp is required")
    try:
        timestamp = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid retrieval timestamp") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Retrieval timestamp must include timezone")
    return {
        "source_url": source_url,
        "sha256": hashlib.sha256(content_bytes).hexdigest(),
        "byte_count": len(content_bytes),
        "retrieved_at": retrieved_at,
        "status": "DISCOVERY_ONLY",
        "historical_snapshot_verified": False,
        "blind_eligible": False,
        "accuracy_evaluated": False,
    }
