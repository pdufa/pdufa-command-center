from hashlib import sha256

from research.fda_outcome_document_integrity import check_outcome_document


def test_matching_bytes_do_not_prove_fda_origin(tmp_path):
    path = tmp_path / "decision.pdf"
    content = b"%PDF-1.4\nresearch fixture\n"
    path.write_bytes(content)
    expected = sha256(content).hexdigest()
    result = check_outcome_document(
        path, pinned_sha256=expected,
        independently_authenticated_digest=True,
    )
    assert result.status == "BYTES_MATCH_ORIGIN_UNVERIFIED"
    assert result.actual_sha256 == expected


def test_mismatch_and_missing_document(tmp_path):
    path = tmp_path / "decision.pdf"
    path.write_bytes(b"not the expected decision")
    expected = sha256(b"expected").hexdigest()
    assert check_outcome_document(path, pinned_sha256=expected).status == "DOCUMENT_DIGEST_MISMATCH"
    assert check_outcome_document(tmp_path / "missing.pdf", pinned_sha256=expected).status == "DOCUMENT_UNAVAILABLE"


def test_invalid_digest_rejected(tmp_path):
    assert check_outcome_document(tmp_path / "anything", pinned_sha256="invalid").status == "INVALID_PINNED_DIGEST"
