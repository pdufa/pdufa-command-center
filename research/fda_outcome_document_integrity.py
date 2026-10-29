"""Research-only FDA decision document byte-integrity check.

A matching SHA-256 verifies bytes against a pinned digest; it does not
authenticate the FDA as publisher. The digest must come from an
independently authenticated source.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re


_SHA = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class DocumentIntegrity:
    status: str
    actual_sha256: str | None


def check_outcome_document(
    path: str | Path,
    *,
    pinned_sha256: str,
    independently_authenticated_digest: bool = False,
) -> DocumentIntegrity:
    if not isinstance(pinned_sha256, str) or not _SHA.fullmatch(pinned_sha256):
        return DocumentIntegrity("INVALID_PINNED_DIGEST", None)
    try:
        digest = sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return DocumentIntegrity("DOCUMENT_UNAVAILABLE", None)
    if digest != pinned_sha256:
        return DocumentIntegrity("DOCUMENT_DIGEST_MISMATCH", digest)
    # Caller-supplied authentication flags are not proof of FDA origin.
    return DocumentIntegrity("BYTES_MATCH_ORIGIN_UNVERIFIED", digest)
