"""Research-only RFC 3161 token verification using OpenSSL.

This verifies a timestamp response token against a caller-provisioned trusted
CA bundle and expected SHA-256 message imprint. It does not establish that
the CA bundle is independently trusted, or that the timestamp predates a
specific cutoff. Those are separate admission requirements.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class RFC3161Verification:
    status: str
    cryptographically_verified: bool = False


def verify_rfc3161_token(
    token_der: bytes,
    *,
    expected_imprint_sha256: str,
    trusted_ca_pem: bytes,
    pinned_ca_bundle_sha256: str,
    openssl_binary: str = "openssl",
) -> RFC3161Verification:
    import tempfile

    if not token_der or not trusted_ca_pem:
        return RFC3161Verification("MISSING_TOKEN_OR_TRUST_BUNDLE")
    if len(expected_imprint_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_imprint_sha256):
        return RFC3161Verification("INVALID_IMPRINT")
    if sha256(trusted_ca_pem).hexdigest() != pinned_ca_bundle_sha256:
        return RFC3161Verification("CA_BUNDLE_PIN_MISMATCH")
    with tempfile.TemporaryDirectory(prefix="pdufa-tsa-") as tmp:
        token = Path(tmp) / "token.der"
        ca = Path(tmp) / "trusted-ca.pem"
        token.write_bytes(token_der)
        ca.write_bytes(trusted_ca_pem)
        try:
            proc = subprocess.run(
                [openssl_binary, "ts", "-verify", "-token_in", "-in", str(token),
                 "-digest", expected_imprint_sha256, "-CAfile", str(ca)],
                capture_output=True, text=True, timeout=20, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return RFC3161Verification("VERIFIER_UNAVAILABLE")
    if proc.returncode != 0:
        return RFC3161Verification("TOKEN_SIGNATURE_OR_IMPRINT_INVALID")
    # Successful OpenSSL validation alone does not independently authenticate
    # the operator's trust-root selection or establish cutoff chronology.
    return RFC3161Verification("OPENSSL_SIGNATURE_VERIFIED_CA_TRUST_NOT_ATTESTED", True)
