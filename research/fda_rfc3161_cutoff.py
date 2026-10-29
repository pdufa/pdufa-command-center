"""Cutoff chronology for cryptographically verified RFC 3161 timestamps.

The caller must provide a verifier-derived generation time, not a self-declared
receipt time. This module cannot itself authenticate that provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone

from research.fda_rfc3161_openssl_verifier import RFC3161Verification


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Timezone required")
    return parsed.astimezone(timezone.utc)


def check_verified_timestamp_cutoff(
    verification: RFC3161Verification,
    *,
    token_generation_time_utc: str,
    prediction_recorded_at_utc: str,
    prediction_cutoff_utc: str,
    fda_decision_at_utc: str,
) -> str:
    if not verification.cryptographically_verified:
        return "TOKEN_NOT_CRYPTOGRAPHICALLY_VERIFIED"
    try:
        generated = _utc(token_generation_time_utc)
        recorded = _utc(prediction_recorded_at_utc)
        cutoff = _utc(prediction_cutoff_utc)
        decision = _utc(fda_decision_at_utc)
    except (ValueError, TypeError, AttributeError):
        return "INVALID_TIMESTAMP"
    if generated < recorded:
        return "TOKEN_PREDATES_RECORDED_PREDICTION"
    if generated > cutoff:
        return "TOKEN_AFTER_CUTOFF"
    if cutoff >= decision:
        return "CUTOFF_NOT_BEFORE_FDA_DECISION"
    # The token time is supplied separately; its cryptographic binding to
    # the verified token has NOT been established by this helper.
    return "CHRONOLOGY_PLAUSIBLE_TOKEN_TIME_BINDING_UNVERIFIED"
