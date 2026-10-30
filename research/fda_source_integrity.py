"""Offline research-only verification of evidence document bytes.

No network fetch, no production wiring, no claims about FDA decisions.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class DocumentRecord:
    document_id: str
    expected_sha256: str
    source_url: str
    reviewer: str
    reviewed_at_utc: str


def verify_document_bytes(path: str | Path, record: DocumentRecord) -> bool:
    """Verify local bytes against a supplied SHA-256 digest.

    Digest agreement confirms byte integrity relative to the recorded
    digest; it does NOT prove origin, authenticity, or independent review.
    """
    if not all((
        record.document_id.strip(), record.source_url.strip(),
        record.reviewer.strip(), record.reviewed_at_utc.strip(),
    )):
        return False
    if not _SHA256.fullmatch(record.expected_sha256):
        return False
    file_path = Path(path)
    if not file_path.is_file():
        return False
    digest = sha256()
    with file_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest() == record.expected_sha256
