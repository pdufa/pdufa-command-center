from hashlib import sha256

from research.fda_official_document_fetch import FDADocumentFetch
from research.fda_outcome_evidence_adjudication import inspect_outcome_adjudication
from research.fda_outcome_identity_gate import FDAOutcomeIdentityEvidence, FDAProgramIdentity
from research.fda_outcome_source_manifest import OutcomeSourceManifest


def test_consistent_local_fda_evidence_still_requires_independent_review(tmp_path):
    path = tmp_path / "decision.pdf"
    data = b"research fixture only"
    path.write_bytes(data)
    digest = sha256(data).hexdigest()
    url = "https://www.fda.gov/drugs/example"
    program = FDAProgramIdentity("TRIAL-1", "NDA-123456", "Drug A", "Indication A")
    identity = FDAOutcomeIdentityEvidence(
        "NDA-123456", "Drug A", "Indication A", "PASS", digest
    )
    manifest = OutcomeSourceManifest("TRIAL-1", "NDA-123456", "PASS", url, digest)
    retrieval = FDADocumentFetch(
        "HTTPS_BYTES_CAPTURED_DECISION_UNVERIFIED", url,
        document_sha256=digest, document_bytes=data,
    )
    result = inspect_outcome_adjudication(
        program, identity, manifest, path, retrieval
    )
    assert result.identity_gate == "IDENTITY_MATCHED_FDA_DECISION_NOT_AUTHENTICATED"
    assert result.document_gate == "LOCAL_BYTES_MATCH_FDA_ORIGIN_UNVERIFIED"
    assert result.retrieval_gate == "RETRIEVAL_BYTES_MATCH_DECISION_UNVERIFIED"
    assert not result.accepted_as_verified_outcome
