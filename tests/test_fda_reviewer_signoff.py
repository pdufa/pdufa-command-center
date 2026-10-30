import base64
from dataclasses import replace

import pytest

from research.fda_reviewer_signoff import (
    SignedReview, canonical_payload, verify_review_signature,
)


def test_unsigned_or_unknown_reviewer_rejected():
    review = SignedReview("unknown", "doc-1", "a" * 64, "reviewed", "2026-10-28T00:00:00Z", "")
    assert not verify_review_signature(review, {})
    assert not verify_review_signature(replace(review, signature_base64="bad"), {})


def test_signature_authenticates_exact_review_payload():
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    private = ed25519.Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    unsigned = SignedReview("reviewer-1", "doc-1", "a" * 64, "CONFORMANT", "2026-10-28T00:00:00Z", "")
    signed = replace(unsigned, signature_base64=base64.b64encode(private.sign(canonical_payload(unsigned))).decode())
    assert verify_review_signature(signed, {"reviewer-1": public})
    assert not verify_review_signature(replace(signed, finding="NONCONFORMANT"), {"reviewer-1": public})
    assert not verify_review_signature(signed, {"other-reviewer": public})
