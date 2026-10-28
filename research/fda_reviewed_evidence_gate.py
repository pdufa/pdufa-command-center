"""Research-only independent review gate for trial-population adjudication.

A hash verifies bytes, not their provenance or scientific interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from research.fda_source_integrity import DocumentRecord, verify_document_bytes
from research.tnxp_resilient_itt_gate import Adjudication


REQUIRED_DOCUMENT_ROLES = frozenset({
    "final_sap", "sap_version_history", "database_lock_record",
    "csr_population_listing", "protocol_deviation",
    "exclusion_adjudication", "all_randomized_sensitivity",
})


@dataclass(frozen=True)
class ReviewedSource:
    role: str
    path: str
    record: DocumentRecord
    provenance_verified: bool
    reviewer_independent: bool
    review_finding: str
    review_timestamp_utc: str


def _valid_utc_timestamp(value: str) -> bool:
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return timestamp.tzinfo is not None and timestamp.utcoffset() is not None
    except (ValueError, TypeError):
        return False


def adjudicate_reviewed_sources(
    sources: Mapping[str, ReviewedSource],
    *,
    scientific_finding: str | None = None,
) -> Adjudication:
    """Require every source role, byte verification and independent review.

    scientific_finding must be explicit; this function does not infer
    compliance from file presence. Provenance/reviewer attestations remain
    externally asserted until verified by a trusted process. Therefore
    this function deliberately returns UNRESOLVED even when all checks pass.
    """
    if set(sources) != REQUIRED_DOCUMENT_ROLES:
        return Adjudication.UNRESOLVED
    if scientific_finding not in {"CONFORMANT", "NONCONFORMANT"}:
        return Adjudication.UNRESOLVED
    for role, source in sources.items():
        if source.role != role or not source.provenance_verified:
            return Adjudication.UNRESOLVED
        if not source.reviewer_independent or not source.review_finding.strip():
            return Adjudication.UNRESOLVED
        if not _valid_utc_timestamp(source.review_timestamp_utc):
            return Adjudication.UNRESOLVED
        if not verify_document_bytes(Path(source.path), source.record):
            return Adjudication.UNRESOLVED
    # Source metadata can be self-asserted. Trusted reviewer identity,
    # provenance and signoff need a separate verifiable trust boundary.
    return Adjudication.UNRESOLVED
