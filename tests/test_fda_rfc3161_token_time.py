from unittest.mock import patch
import subprocess

from research.fda_rfc3161_token_time import token_time_before_cutoff


def test_requires_verified_signature(tmp_path):
    assert token_time_before_cutoff(tmp_path / "missing.tsr", "2026-12-01T00:00:00Z") == "SIGNATURE_NOT_VERIFIED"


def test_token_generation_time_comparison(tmp_path):
    token = tmp_path / "token.tsr"
    token.write_bytes(b"fixture")
    with patch("research.fda_rfc3161_token_time.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "Time stamp: Nov 01 00:00:00 2026 GMT\n", "")
        early = token_time_before_cutoff(token, "2026-12-01T00:00:00Z", signature_and_imprint_verified=True)
        late = token_time_before_cutoff(token, "2026-10-01T00:00:00Z", signature_and_imprint_verified=True)
    assert early == "TOKEN_TIME_BEFORE_CUTOFF_POLICY_UNVERIFIED"
    assert late == "TOKEN_ISSUED_AFTER_CUTOFF"


def test_missing_time_rejected(tmp_path):
    token = tmp_path / "token.tsr"
    token.write_bytes(b"fixture")
    with patch("research.fda_rfc3161_token_time.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 0, "No time here", "")
        assert token_time_before_cutoff(
            token, "2026-12-01T00:00:00Z", signature_and_imprint_verified=True
        ) == "TOKEN_TIME_UNREADABLE"
