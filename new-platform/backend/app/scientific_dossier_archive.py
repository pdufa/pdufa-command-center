"""Build an eight-domain dossier from an existing verified trial archive.

Pure read-only adapter: no ORM connection, scheduler, registry network call,
candidate ranking, preset change, or scientific-score generation.
"""
from __future__ import annotations

import gzip
import hashlib
import hmac
import io
import json
import re
from datetime import datetime
from typing import Any

from .scientific_dossier import build_scientific_dossier

MAX_ARCHIVE_BYTES = 10_000_000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def dossier_from_archive(
    exact_id: str,
    nct_id: str,
    payload_gzip: bytes,
    expected_sha256: str,
    fetched_at: datetime | None = None,
) -> dict[str, Any]:
    """Verify an archived source byte-for-byte before producing its dossier.

    Claims stay source-record-only, including when metadata appear complete.
    A source mismatch or truncated archive fails closed without returning a
    partial dossier.
    """
    if not isinstance(payload_gzip, bytes):
        raise ValueError("Archived payload must be bytes")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        raise ValueError("Invalid archived SHA256")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload_gzip), mode="rb") as stream:
            raw = stream.read(MAX_ARCHIVE_BYTES + 1)
            if len(raw) > MAX_ARCHIVE_BYTES:
                raise ValueError("Archived record exceeds size limit")
            if stream.read(1):
                raise ValueError("Archived record exceeds size limit")
    except (OSError, EOFError) as exc:
        raise ValueError("Corrupt archived trial payload") from exc
    if not hmac.compare_digest(hashlib.sha256(raw).hexdigest(), expected_sha256):
        raise ValueError("Archived record checksum mismatch")
    try:
        record = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Archived record is not valid JSON") from exc
    if not isinstance(record, dict):
        raise ValueError("Archived trial record must be an object")
    dossier = build_scientific_dossier(exact_id, nct_id, record)
    if dossier["source_sha256"] != expected_sha256:
        raise ValueError("Archived record must have canonical source checksum")
    if fetched_at is not None:
        if not isinstance(fetched_at, datetime) or fetched_at.tzinfo is None:
            raise ValueError("Archive timestamp must be timezone-aware")
        dossier["source_fetched_at"] = fetched_at.isoformat()
    return dossier
