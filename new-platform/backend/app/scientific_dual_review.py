"""Independent scientific review decision contract; no automatic score promotion.

Google identity establishes a subject, not professional qualifications or a
scientific verdict. This module refuses self-approval and unaudited decisions.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

REQUIRED_ATTESTATIONS = (
    "source_content_inspected",
    "clinical_method_reconciled",
    "conflicts_disclosed",
    "qualifications_checked",
)


def audit_digest(record: Mapping) -> str:
    """Canonical digest for a durable record; not a cryptographic signature."""
    if not isinstance(record, Mapping):
        raise ValueError("Audit record required")
    raw = json.dumps(dict(record), sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def dual_review_preflight(first: Mapping, second: Mapping) -> dict:
    """Validate two independent identity/role attestations without adjudicating.

    Caller must load identities, permissions, source attestations and audit
    history from trusted server storage; never accept client-supplied booleans.
    """
    if not isinstance(first, Mapping) or not isinstance(second, Mapping):
        raise ValueError("Two trusted reviewer records required")
    required = ("nctId", "questionId", "sourceSha256", "decision")
    if any(not first.get(k) or first.get(k) != second.get(k) for k in required):
        raise ValueError("Reviews must match trial, question, source and decision")
    a, b = first.get("googleSubject"), second.get("googleSubject")
    if not isinstance(a, str) or not isinstance(b, str) or not a or a == b:
        raise ValueError("Distinct immutable Google subjects required")
    for record in (first, second):
        if record.get("identityVerified") is not True:
            raise ValueError("Google identity verification required")
        if record.get("roleAuthorized") is not True:
            raise ValueError("Explicit scientific reviewer authorization required")
        if record.get("credentialsVerified") is not True:
            raise ValueError("Professional qualification review required")
        if record.get("sourceIndependentlyVerified") is not True:
            raise ValueError("Independent source content verification required")
        if any(record.get(field) is not True for field in REQUIRED_ATTESTATIONS):
            raise ValueError("Incomplete scientific reviewer attestations")
        if record.get("auditPersisted") is not True:
            raise ValueError("Durable reviewer audit record required")
    return {
        "nctId": first["nctId"],
        "questionId": first["questionId"],
        "independentReviewerCount": 2,
        "preflightPassed": True,
        "scientificConclusion": None,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "mayAutoPromoteReadiness": False,
        "note": "Prerequisite checks only; a separate adjudication process is required.",
    }
