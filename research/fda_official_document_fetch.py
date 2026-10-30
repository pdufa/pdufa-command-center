"""Research-only retrieval of publicly accessible FDA documents.

HTTPS transport and SHA-256 integrity do not establish that the bytes are
an official decision letter, a CRL, or the outcome of a particular program.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler
import urllib.error


@dataclass(frozen=True)
class FDADocumentFetch:
    status: str
    source_url: str
    retrieved_at_utc: str | None = None
    document_sha256: str | None = None
    document_bytes: bytes | None = None
    content_type: str | None = None
    independently_authenticated_decision: bool = False


def _official_https(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (parsed.scheme == "https" and parsed.port in (None, 443)
            and not parsed.username and not parsed.password
            and (host == "fda.gov" or host.endswith(".fda.gov")))


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_public_fda_document(url: str, *, max_bytes: int = 10_000_000) -> FDADocumentFetch:
    if not _official_https(url):
        return FDADocumentFetch("NON_OFFICIAL_OR_UNSAFE_URL", url)
    if max_bytes < 1 or max_bytes > 50_000_000:
        return FDADocumentFetch("INVALID_SIZE_LIMIT", url)
    try:
        request = Request(url, headers={"User-Agent": "PDUFA-Research-Evidence/1.0"})
        with build_opener(_NoRedirects()).open(request, timeout=15) as response:
            content = response.read(max_bytes + 1)
            content_type = response.headers.get("Content-Type", "")
        if len(content) > max_bytes:
            return FDADocumentFetch("DOCUMENT_TOO_LARGE", url)
        return FDADocumentFetch(
            "HTTPS_BYTES_CAPTURED_DECISION_UNVERIFIED",
            url,
            datetime.now(timezone.utc).isoformat(),
            sha256(content).hexdigest(),
            content,
            content_type,
        )
    except (OSError, urllib.error.URLError, ValueError):
        return FDADocumentFetch("RETRIEVAL_FAILED", url)
