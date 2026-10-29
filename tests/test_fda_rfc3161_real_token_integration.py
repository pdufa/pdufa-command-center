"""Opt-in integration test for genuine RFC 3161 evidence.

Environment variables must point to independently obtained fixture files.
CI skips when not provisioned; a skip is not proof of verification.
"""
from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path

import pytest

from research.fda_rfc3161_token_time import verify_token_time_before_cutoff


@pytest.mark.integration
def test_genuine_token_bound_to_imprint_and_pre_cutoff():
    names = (
        "PDUFA_TSA_TOKEN_DER_FILE",
        "PDUFA_TSA_TRUSTED_CA_PEM_FILE",
        "PDUFA_TSA_CA_BUNDLE_SHA256",
        "PDUFA_TSA_EXPECTED_IMPRINT_SHA256",
        "PDUFA_TSA_TEST_CUTOFF_UTC",
    )
    if not all(os.getenv(name) for name in names):
        pytest.skip("Genuine TSA fixture not configured; no external timestamp claim")
    token = Path(os.environ[names[0]]).read_bytes()
    ca = Path(os.environ[names[1]]).read_bytes()
    pin = os.environ[names[2]]
    assert sha256(ca).hexdigest() == pin, "Fixture CA bundle differs from pinned value"
    result = verify_token_time_before_cutoff(
        token,
        os.environ[names[4]],
        expected_imprint_sha256=os.environ[names[3]],
        trusted_ca_pem=ca,
        pinned_ca_bundle_sha256=pin,
    )
    assert result == "TOKEN_TIME_BEFORE_CUTOFF_CA_POLICY_NOT_INDEPENDENTLY_ATTESTED"
