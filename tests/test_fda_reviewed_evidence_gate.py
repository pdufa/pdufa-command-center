from hashlib import sha256

from research.fda_reviewed_evidence_gate import (
    REQUIRED_DOCUMENT_ROLES,
    ReviewedSource,
    adjudicate_reviewed_sources,
)
from research.fda_source_integrity import DocumentRecord
from research.tnxp_resilient_itt_gate import Adjudication


def test_empty_and_incomplete_sources_abstain():
    assert adjudicate_reviewed_sources({}) is Adjudication.UNRESOLVED
    assert adjudicate_reviewed_sources({}, scientific_finding="CONFORMANT") is Adjudication.UNRESOLVED


def test_all_self_attested_sources_still_cannot_certify(tmp_path):
    data = b"test fixture only"
    file = tmp_path / "fixture.pdf"
    file.write_bytes(data)
    sources = {}
    for role in REQUIRED_DOCUMENT_ROLES:
        record = DocumentRecord(
            document_id=role,
            expected_sha256=sha256(data).hexdigest(),
            source_url="https://example.org/fixture.pdf",
            reviewer="unverified",
            reviewed_at_utc="2026-10-28T20:00:00Z",
        )
        sources[role] = ReviewedSource(
            role=role,
            path=str(file),
            record=record,
            provenance_verified=True,
            reviewer_independent=True,
            review_finding="self asserted",
            review_timestamp_utc="2026-10-28T20:00:00Z",
        )
    assert adjudicate_reviewed_sources(
        sources, scientific_finding="CONFORMANT"
    ) is Adjudication.UNRESOLVED
    assert adjudicate_reviewed_sources(
        sources, scientific_finding="NONCONFORMANT"
    ) is Adjudication.UNRESOLVED
