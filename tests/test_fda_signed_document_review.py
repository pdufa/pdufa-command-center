import base64
from dataclasses import replace
from hashlib import sha256

import pytest

from research.fda_reviewer_signoff import SignedReview, canonical_payload
from research.fda_signed_document_review import DocumentReviewBundle, verify_signed_document_review
from research.fda_source_integrity import DocumentRecord


def test_signed_review_bound_to_verified_bytes(tmp_path):
    ed25519 = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    serialization = pytest.importorskip("cryptography.hazmat.primitives.serialization")
    key = ed25519.Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw,
    )
    data = b"local evidence bytes"
    path = tmp_path / "evidence.pdf"
    path.write_bytes(data)
    digest = sha256(data).hexdigest()
    document = DocumentRecord("doc-1", digest, "https://example.org/document", "reviewer-1", "2026-10-28T00:00:00Z")
    unsigned = SignedReview("reviewer-1", "doc-1", digest, "reviewed", "2026-10-28T00:00:00Z", "")
    signed = replace(unsigned, signature_base64=base64.b64encode(key.sign(canonical_payload(unsigned))).decode())
    bundle = DocumentReviewBundle(str(path), document, signed)
    trusted = {"reviewer-1": public}
    assert verify_signed_document_review(bundle, trusted)
    assert not verify_signed_document_review(replace(bundle, document=replace(document, document_id="other")), trusted)
    assert not verify_signed_document_review(replace(bundle, review=replace(signed, sha256="0" * 64)), trusted)
    path.write_bytes(b"tampered")
    assert not verify_signed_document_review(bundle, trusted)
