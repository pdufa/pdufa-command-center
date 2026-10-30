"""Research-only FDA outcome source evidence manifest.

This checks local evidence consistency. A matching digest or FDA-looking URL
does not authenticate a confidential CRL or prove official FDA provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class OutcomeSourceManifest:
    trial_id: str
    application_number: str
    decision: str
    source_url: str
    original_document_sha256: str
    reviewer_id: str = ""


@dataclass(frozen=True)
class OutcomeSourceCheck:
    status: str
    independently_authenticated: bool = False


def inspect_outcome_source(
    manifest: OutcomeSourceManifest,
    document_path: str | Path,
    *,
    expected_trial_id: str,
) -> OutcomeSourceCheck:
    if manifest.trial_id != expected_trial_id:
        return OutcomeSourceCheck("TRIAL_ID_MISMATCH")
    if manifest.decision not in {"PASS", "CRL", "EXTENSION"}:
        return OutcomeSourceCheck("UNSUPPORTED_DECISION")
    if not manifest.application_number.strip():
        return OutcomeSourceCheck("MISSING_APPLICATION_NUMBER")
    parsed = urlparse(manifest.source_url)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return OutcomeSourceCheck("INVALID_SOURCE_URL")
    host = (parsed.hostname or "").lower()
    if host != "fda.gov" and not host.endswith(".fda.gov"):
        return OutcomeSourceCheck("NON_FDA_SOURCE")
    try:
        content = Path(document_path).read_bytes()
    except OSError:
        return OutcomeSourceCheck("DOCUMENT_UNAVAILABLE")
    if sha256(content).hexdigest() != manifest.original_document_sha256:
        return OutcomeSourceCheck("DOCUMENT_DIGEST_MISMATCH")
    # No authenticated retrieval transcript, document identity binding,
    # independent reviewer signature, or source publication audit exists yet.
    return OutcomeSourceCheck("LOCAL_BYTES_MATCH_FDA_ORIGIN_UNVERIFIED")
