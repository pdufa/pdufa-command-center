"""Research-only RFC3161 token time inspection, following signature verification.

OpenSSL textual token inspection is not a full TSA policy validation.
Only call this after independently verifying the same token signature.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re
import subprocess


_STAMP = re.compile(r"^Time stamp:\s*(.+?)\s*$", re.MULTILINE)
_FORMATS = ("%b %d %H:%M:%S %Y GMT", "%b %d %H:%M:%S.%f %Y GMT")


def token_time_before_cutoff(
    token_path: str | Path, cutoff_utc: str, *,
    signature_and_imprint_verified: bool = False,
    openssl_binary: str = "openssl",
) -> str:
    if not signature_and_imprint_verified:
        return "SIGNATURE_NOT_VERIFIED"
    try:
        cutoff = datetime.fromisoformat(cutoff_utc.replace("Z", "+00:00"))
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            return "INVALID_CUTOFF"
        if not Path(token_path).is_file():
            return "TOKEN_UNAVAILABLE"
        result = subprocess.run(
            [openssl_binary, "ts", "-reply", "-in", str(token_path),
             "-token_in", "-text"],
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
        return "TOKEN_TIME_BEFORE_CUTOFF_POLICY_UNVERIFIED"
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, AttributeError):
        return "TOKEN_TIME_CHECK_FAILED"
