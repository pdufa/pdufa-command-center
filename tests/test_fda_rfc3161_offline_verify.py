from unittest.mock import patch
import subprocess

from research.fda_rfc3161_offline_verify import verify_rfc3161_token


def test_missing_evidence_fails_closed(tmp_path):
    result = verify_rfc3161_token(
        token_path=tmp_path / "missing.tsr",
        original_data_path=tmp_path / "missing.jsonl",
        tsa_ca_bundle_path=tmp_path / "missing.pem",
    )
    assert result.status == "MISSING_TOKEN_DATA_OR_TRUST_STORE"
    assert not result.cryptographically_valid
    assert not result.independently_trusted_time


def test_successful_crypto_still_requires_policy_review(tmp_path):
    paths = [tmp_path / name for name in ("receipt.tsr", "ledger.jsonl", "trusted.pem")]
    for path in paths:
        path.write_bytes(b"fixture")
    with patch("research.fda_rfc3161_offline_verify.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "Verification: OK", "")
        result = verify_rfc3161_token(
            token_path=paths[0], original_data_path=paths[1],
            tsa_ca_bundle_path=paths[2],
        )
    assert result.cryptographically_valid
    assert not result.independently_trusted_time
    assert result.status == "TOKEN_SIGNATURE_AND_IMPRINT_VALID_POLICY_PENDING"


def test_crypto_failure_fails_closed(tmp_path):
    paths = [tmp_path / name for name in ("receipt.tsr", "ledger.jsonl", "trusted.pem")]
    for path in paths:
        path.write_bytes(b"fixture")
    with patch("research.fda_rfc3161_offline_verify.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 1, "", "verification failure")
        result = verify_rfc3161_token(
            token_path=paths[0], original_data_path=paths[1],
            tsa_ca_bundle_path=paths[2],
        )
    assert result.status == "TOKEN_VERIFICATION_FAILED"
    assert not result.cryptographically_valid
