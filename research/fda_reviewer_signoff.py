"""Research-only cryptographic reviewer-signoff verification.

Trusted reviewer public keys must be provisioned independently of the
submitted evidence. Signatures prove possession of a corresponding key,
not reviewer independence or the authenticity of the underlying source.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from typing import Mapping


@dataclass(frozen=True)
class SignedReview:
    reviewer_id: str
    document_id: str
    sha256: str
    finding: str
    reviewed_at_utc: str
    signature_base64: str


def canonical_payload(review: SignedReview) -> bytes:
    return json.dumps(
        {
            "document_id": review.document_id,
            "finding": review.finding,
            "reviewed_at_utc": review.reviewed_at_utc,
            "reviewer_id": review.reviewer_id,
            "sha256": review.sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def verify_review_signature(
    review: SignedReview, trusted_public_keys: Mapping[str, bytes]
) -> bool:
    """Check Ed25519 signature using a separately trusted reviewer key.

    Fail closed if cryptography is unavailable, key is unknown, payload
    fields are missing, or signature is invalid.
    """
    if not all((
        review.reviewer_id.strip(), review.document_id.strip(),
        review.sha256.strip(), review.finding.strip(),
        review.reviewed_at_utc.strip(), review.signature_base64.strip(),
    )):
        return False
    if review.reviewer_id not in trusted_public_keys:
        return False
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = Ed25519PublicKey.from_public_bytes(trusted_public_keys[review.reviewer_id])
        signature = base64.b64decode(review.signature_base64, validate=True)
        key.verify(signature, canonical_payload(review))
    except (ImportError, ValueError, TypeError, Exception):
        return False
    return True
