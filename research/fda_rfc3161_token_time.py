"""Research-only RFC 3161 token-time checks.

The integrated entry point verifies signature and imprint on the same token
before reading its signed generation time. Independent TSA trust policy is
not established by these helpers.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess
import tempfile

from research.fda_rfc3161_openssl_verifier import verify_rfc3161_token

_STAMP = re.compile(r"^Time stamp:\s*(.+?)\s*$", re.MULTILINE)
_FORMATS = ("%b %d %H:%M:%S %Y GMT", "%b %d %H:%M:%S.%f %Y GMT")


def token_time_before_cutoff(
    token_path: str | Path, cutoff_utc: str, *,
    signature_and_imprint_verified: bool = False,
    openssl_binary: str = "openssl",
) -> str:
    """Legacy helper: caller assertion cannot establish verified token time."""
    return "USE_INTEGRATED_TOKEN_VERIFICATION"


def verify_token_time_before_cutoff(
    token_der: bytes, cutoff_utc: str, *,
    expected_imprint_sha256: str,
    trusted_ca_pem: bytes,
    pinned_ca_bundle_sha256: str,
    openssl_binary: str = "openssl",
) -> str:
    verified = verify_rfc3161_token(
        token_der,
        expected_imprint_sha256=expected_imprint_sha256,
        trusted_ca_pem=trusted_ca_pem,
        pinned_ca_bundle_sha256=pinned_ca_bundle_sha256,
        openssl_binary=openssl_binary,
    )
    if not verified.cryptographically_verified:
        return verified.status
    try:
        cutoff = datetime.fromisoformat(cutoff_utc.replace("Z", "+00:00"))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            return "INVALID_CUTOFF"
        with tempfile.TemporaryDirectory(prefix="pdufa-ts-time-") as tmp:
            path = Path(tmp) / "token.der"
            path.write_bytes(token_der)
            result = subprocess.run(
                [openssl_binary, "ts", "-reply", "-in", str(path), "-token_in", "-text"],
                capture_output=True, text=True, timeout=20, check=False,
            )
        if result.returncode:
            return "TOKEN_INSPECTION_FAILED"
        matches = _STAMP.findall(result.stdout)
        if len(matches) != 1:
            return "TOKEN_TIME_UNREADABLE"
        issued = None
        for fmt in _FORMATS:
            try:
                issued = datetime.strptime(matches[0], fmt).replace(tzinfo=timezone.utc)
                break
            except ValueError:
                continue
        if issued is None:
            return "TOKEN_TIME_UNREADABLE"
        if issued > cutoff.astimezone(timezone.utc):
            return "TOKEN_ISSUED_AFTER_CUTOFF"
        return "TOKEN_TIME_BEFORE_CUTOFF_CA_POLICY_NOT_INDEPENDENTLY_ATTESTED"
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, AttributeError):
        return "TOKEN_TIME_CHECK_FAILED"
