"""Research-only identity gate for FDA outcome evidence.

Matching identifiers is necessary but insufficient: actual FDA decision
authentication and independent reviewer adjudication remain outstanding.
"""
from __future__ import annotations

from dataclasses import dataclass
import re


_APPLICATION = re.compile(r"^(?:NDA|BLA|ANDA)[- ]?\d{5,6}$", re.IGNORECASE)


@dataclass(frozen=True)
class FDAProgramIdentity:
    trial_id: str
    application_number: str
    product_name: str
    indication: str


@dataclass(frozen=True)
class FDAOutcomeIdentityEvidence:
    application_number: str
    product_name: str
    indication: str
    decision: str
    document_sha256: str


def _norm(value: str) -> str:
    return " ".join(value.casefold().strip().split())


def check_outcome_identity(
    program: FDAProgramIdentity,
    evidence: FDAOutcomeIdentityEvidence,
) -> str:
    if not program.trial_id.strip():
        return "MISSING_TRIAL_ID"
    if not _APPLICATION.fullmatch(program.application_number.strip()):
        return "INVALID_APPLICATION_NUMBER"
    if not program.product_name.strip() or not program.indication.strip():
        return "INCOMPLETE_PROGRAM_IDENTITY"
    if _norm(program.application_number).replace("-", "").replace(" ", "") != (
        _norm(evidence.application_number).replace("-", "").replace(" ", "")
    ):
        return "APPLICATION_MISMATCH"
    if _norm(program.product_name) != _norm(evidence.product_name):
        return "PRODUCT_MISMATCH"
    if _norm(program.indication) != _norm(evidence.indication):
        return "INDICATION_MISMATCH"
    if evidence.decision not in {"PASS", "CRL", "EXTENSION"}:
        return "UNSUPPORTED_DECISION"
    if not re.fullmatch(r"[a-f0-9]{64}", evidence.document_sha256):
        return "INVALID_DOCUMENT_DIGEST"
    return "IDENTITY_MATCHED_FDA_DECISION_NOT_AUTHENTICATED"
