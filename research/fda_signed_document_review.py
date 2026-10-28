"""Research-only signed review + local document integrity validation.

Verifies exact bytes and a signature from a separately supplied trusted
public key. Does not assert FDA provenance, reviewer independence, or
regulatory correctness. No production use.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from research.fda_reviewer_signoff import SignedReview, verify_review_signature
from research.fda_source_integrity import DocumentRecord, verify_document_bytes


@dataclass(frozen=True)
class DocumentReviewBundle:
    file_path: str
    document: DocumentRecord
    review: SignedReview


def verify_signed_document_review(
    bundle: DocumentReviewBundle, trusted_public_keys: Mapping[str, bytes]
) -> bool:
    """Require a valid signature covering the same document ID and digest."""
    if bundle.review.document_id != bundle.document.document_id:
        return False
    if bundle.review.sha256 != bundle.document.expected_sha256:
        return False
    if bundle.review.reviewer_id != bundle.document.reviewer:
        return False
    if not verify_document_bytes(Path(bundle.file_path), bundle.document):
        return False
    return verify_review_signature(bundle.review, trusted_public_keys)
