"""Fail-closed timestamp evidence admission boundary.

External verifier integration is intentionally absent. A signed local receipt
or arbitrary caller assertion is never sufficient for admission.
"""
from __future__ import annotations

from dataclasses import dataclass

from research.fda_external_timestamp_policy import TimestampAuthorityPolicy, validate_policy


@dataclass(frozen=True)
class TimestampEvidence:
    token_der: bytes
    expected_imprint_sha256: str
    externally_verified: bool = False
    verified_generation_time_utc: str | None = None


@dataclass(frozen=True)
class TimestampGate:
    status: str
    independently_trusted: bool = False


def inspect_timestamp_evidence(
    policy: TimestampAuthorityPolicy,
    evidence: TimestampEvidence,
    *,
    frozen_entry_sha256: str,
) -> TimestampGate:
    valid, _ = validate_policy(policy)
    if not valid:
        return TimestampGate("INVALID_AUTHORITY_POLICY")
    if not evidence.token_der:
        return TimestampGate("MISSING_TIMESTAMP_TOKEN")
    if len(frozen_entry_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in frozen_entry_sha256
    ):
        return TimestampGate("INVALID_FROZEN_DIGEST")
    if evidence.expected_imprint_sha256 != frozen_entry_sha256:
        return TimestampGate("IMPRINT_MISMATCH")
    # Do not trust externally_verified or verified_generation_time_utc fields:
    # both are caller-supplied and no independent verifier is connected.
    return TimestampGate("EXTERNAL_TIMESTAMP_VERIFIER_NOT_CONNECTED")
