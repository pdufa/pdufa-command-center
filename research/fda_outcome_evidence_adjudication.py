"""Research-only FDA outcome evidence adjudication boundary.

All local checks may pass without proving an FDA PASS/CRL/EXTENSION.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from research.fda_official_document_fetch import FDADocumentFetch
from research.fda_outcome_identity_gate import (
    FDAOutcomeIdentityEvidence, FDAProgramIdentity, check_outcome_identity,
)
from research.fda_outcome_source_manifest import (
    OutcomeSourceManifest, inspect_outcome_source,
)


@dataclass(frozen=True)
class OutcomeAdjudication:
    identity_gate: str
    document_gate: str
    retrieval_gate: str
    status: str = "INDEPENDENT_FDA_DECISION_ADJUDICATION_REQUIRED"
    accepted_as_verified_outcome: bool = False


def inspect_outcome_adjudication(
    program: FDAProgramIdentity,
    identity_evidence: FDAOutcomeIdentityEvidence,
    manifest: OutcomeSourceManifest,
    document_path: str | Path,
    retrieval: FDADocumentFetch,
) -> OutcomeAdjudication:
    identity = check_outcome_identity(program, identity_evidence)
    document = inspect_outcome_source(
        manifest, document_path, expected_trial_id=program.trial_id
    ).status
    if retrieval.status != "HTTPS_BYTES_CAPTURED_DECISION_UNVERIFIED":
        retrieval_status = "RETRIEVAL_NOT_VERIFIED"
    elif retrieval.document_sha256 != identity_evidence.document_sha256:
        retrieval_status = "RETRIEVAL_DOCUMENT_DIGEST_MISMATCH"
    elif retrieval.source_url != manifest.source_url:
        retrieval_status = "RETRIEVAL_SOURCE_MISMATCH"
    else:
        retrieval_status = "RETRIEVAL_BYTES_MATCH_DECISION_UNVERIFIED"
    return OutcomeAdjudication(identity, document, retrieval_status)
