from dataclasses import replace
from hashlib import sha256

from research.fda_source_integrity import DocumentRecord, verify_document_bytes


def record_for(data: bytes) -> DocumentRecord:
    return DocumentRecord(
        document_id="TEST-001",
        expected_sha256=sha256(data).hexdigest(),
        source_url="https://example.org/source.pdf",
        reviewer="test-reviewer",
        reviewed_at_utc="2026-10-28T20:00:00Z",
    )


def test_matching_bytes(tmp_path):
    data = b"offline evidence fixture"
    path = tmp_path / "source.pdf"
    path.write_bytes(data)
    assert verify_document_bytes(path, record_for(data))


def test_changed_bytes_rejected(tmp_path):
    data = b"offline evidence fixture"
    path = tmp_path / "source.pdf"
    path.write_bytes(data + b"tampered")
    assert not verify_document_bytes(path, record_for(data))


def test_invalid_digest_and_missing_metadata_rejected(tmp_path):
    data = b"fixture"
    path = tmp_path / "source.pdf"
    path.write_bytes(data)
    record = record_for(data)
    assert not verify_document_bytes(path, replace(record, expected_sha256="abc"))
    assert not verify_document_bytes(path, replace(record, reviewer=""))
    assert not verify_document_bytes(tmp_path / "missing.pdf", record)
