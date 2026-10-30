from research.fda_external_timestamp_policy import TimestampAuthorityPolicy
from research.fda_timestamp_evidence_gate import TimestampEvidence, inspect_timestamp_evidence


POLICY = TimestampAuthorityPolicy("Test authority", "a" * 64, "1.2.3")


def test_caller_claim_cannot_grant_external_trust():
    evidence = TimestampEvidence(
        b"fake-token", "b" * 64,
        externally_verified=True,
        verified_generation_time_utc="2026-01-01T00:00:00Z",
    )
    result = inspect_timestamp_evidence(POLICY, evidence, frozen_entry_sha256="b" * 64)
    assert result.status == "EXTERNAL_TIMESTAMP_VERIFIER_NOT_CONNECTED"
    assert not result.independently_trusted


def test_wrong_imprint_rejected():
    evidence = TimestampEvidence(b"fake-token", "c" * 64)
    result = inspect_timestamp_evidence(POLICY, evidence, frozen_entry_sha256="b" * 64)
    assert result.status == "IMPRINT_MISMATCH"
    assert not result.independently_trusted


def test_missing_token_rejected():
    evidence = TimestampEvidence(b"", "b" * 64)
    result = inspect_timestamp_evidence(POLICY, evidence, frozen_entry_sha256="b" * 64)
    assert result.status == "MISSING_TIMESTAMP_TOKEN"
