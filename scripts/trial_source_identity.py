"""Fail-closed exact trial/protocol identity guard for reviewed source intake.

Call before attaching any external document or numerical finding to a trial.
This is a standalone helper, not a production ingestion integration.
"""
from __future__ import annotations

import re

_NCT = re.compile(r"^NCT[0-9]{8}$")
_PROTOCOL = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)+$")


class SourceIdentityMismatch(ValueError):
    """A document cannot be safely attributed to the requested trial."""


def require_exact_trial_identity(
    *,
    expected_nct: str,
    expected_protocol: str,
    source_nct: str | None,
    source_protocol: str | None,
) -> None:
    """Reject absent, malformed or cross-trial identity, without fuzzy matching.

    The caller must extract both source IDs from the actual original document
    or authoritative registry record, not from a search-result snippet.
    """
    if not isinstance(expected_nct, str) or not _NCT.fullmatch(expected_nct):
        raise SourceIdentityMismatch("Invalid expected NCT identifier")
    if not isinstance(expected_protocol, str) or not _PROTOCOL.fullmatch(expected_protocol):
        raise SourceIdentityMismatch("Invalid expected protocol identifier")
    if not isinstance(source_nct, str) or not _NCT.fullmatch(source_nct):
        raise SourceIdentityMismatch("Missing or invalid source NCT identifier")
    if not isinstance(source_protocol, str) or not _PROTOCOL.fullmatch(source_protocol):
        raise SourceIdentityMismatch("Missing or invalid source protocol identifier")
    if source_nct != expected_nct or source_protocol != expected_protocol:
        raise SourceIdentityMismatch("Source belongs to a different trial or protocol")
