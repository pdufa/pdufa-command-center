from unittest.mock import patch
import subprocess

from research.fda_rfc3161_openssl_verifier import RFC3161Verification
from research.fda_rfc3161_token_time import (
    token_time_before_cutoff, verify_token_time_before_cutoff,
)


KW = dict(expected_imprint_sha256="a" * 64, trusted_ca_pem=b"test-ca", pinned_ca_bundle_sha256="b" * 64)


def test_legacy_caller_flag_cannot_bypass_verification(tmp_path):
    assert token_time_before_cutoff(
        tmp_path / "fixture", "2026-12-01T00:00:00Z",
        signature_and_imprint_verified=True,
    ) == "USE_INTEGRATED_TOKEN_VERIFICATION"


def test_integrated_rejects_unverified_token():
    with patch("research.fda_rfc3161_token_time.verify_rfc3161_token") as verify:
        verify.return_value = RFC3161Verification("TOKEN_INVALID")
        assert verify_token_time_before_cutoff(
            b"fake", "2026-12-01T00:00:00Z", **KW
        ) == "TOKEN_INVALID"


def test_integrated_uses_time_from_same_token():
    with patch("research.fda_rfc3161_token_time.verify_rfc3161_token") as verify, patch(
        "research.fda_rfc3161_token_time.subprocess.run"
    ) as run:
        verify.return_value = RFC3161Verification("OPENSSL_VERIFIED", True)
        run.return_value = subprocess.CompletedProcess(
            [], 0, "Time stamp: Nov 01 00:00:00 2026 GMT\n", ""
        )
        early = verify_token_time_before_cutoff(b"fixture", "2026-12-01T00:00:00Z", **KW)
        late = verify_token_time_before_cutoff(b"fixture", "2026-10-01T00:00:00Z", **KW)
    assert early == "TOKEN_TIME_BEFORE_CUTOFF_CA_POLICY_NOT_INDEPENDENTLY_ATTESTED"
    assert late == "TOKEN_ISSUED_AFTER_CUTOFF"


def test_missing_time_rejected():
    with patch("research.fda_rfc3161_token_time.verify_rfc3161_token") as verify, patch(
        "research.fda_rfc3161_token_time.subprocess.run"
    ) as run:
        verify.return_value = RFC3161Verification("OPENSSL_VERIFIED", True)
        run.return_value = subprocess.CompletedProcess([], 0, "No time here", "")
        assert verify_token_time_before_cutoff(
            b"fixture", "2026-12-01T00:00:00Z", **KW
        ) == "TOKEN_TIME_UNREADABLE"
