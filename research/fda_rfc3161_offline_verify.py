"""Research-only offline RFC 3161 signature and imprint verification.

Requires OpenSSL and an independently provisioned TSA trust store.
This checks token signature and bound data, but does not by itself
adjudicate certificate policy, revocation, or trustworthy issuance time.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class TimestampTokenCheck:
    status: str
    cryptographically_valid: bool
    independently_trusted_time: bool = False


def verify_rfc3161_token(
    *,
    token_path: str | Path,
    original_data_path: str | Path,
    tsa_ca_bundle_path: str | Path,
    openssl_binary: str = "openssl",
) -> TimestampTokenCheck:
    paths = [Path(token_path), Path(original_data_path), Path(tsa_ca_bundle_path)]
    if any(not p.is_file() or p.stat().st_size == 0 for p in paths):
        return TimestampTokenCheck("MISSING_TOKEN_DATA_OR_TRUST_STORE", False)
    # No shell interpolation. OpenSSL's -data verifies the signed message imprint.
    try:
        process = subprocess.run(
            [openssl_binary, "ts", "-verify", "-token_in",
             "-in", str(paths[0]), "-data", str(paths[1]),
             "-CAfile", str(paths[2])],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return TimestampTokenCheck("VERIFIER_UNAVAILABLE", False)
    if process.returncode != 0:
        return TimestampTokenCheck("TOKEN_VERIFICATION_FAILED", False)
    # Successful OpenSSL verification alone does not satisfy full trust policy.
    return TimestampTokenCheck("TOKEN_SIGNATURE_AND_IMPRINT_VALID_POLICY_PENDING", True)
