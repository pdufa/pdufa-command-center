"""External timestamp trust policy — configuration only, not a TSA client.

RFC 3161 token validation must be performed by a separately reviewed
cryptographic verifier. This module never grants timestamp trust.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TimestampAuthorityPolicy:
    authority_name: str
    trust_anchor_sha256: str
    required_policy_oid: str
    allowed_hash_algorithm: str = "sha256"


def validate_policy(policy: TimestampAuthorityPolicy) -> tuple[bool, tuple[str, ...]]:
    errors = []
    if not policy.authority_name.strip():
        errors.append("MISSING_AUTHORITY")
    if len(policy.trust_anchor_sha256) != 64 or any(
        char not in "0123456789abcdef" for char in policy.trust_anchor_sha256
    ):
        errors.append("INVALID_TRUST_ANCHOR")
    arcs = policy.required_policy_oid.split(".")
    if len(arcs) < 3 or not all(arc.isdigit() for arc in arcs):
        errors.append("INVALID_POLICY_OID")
    if policy.allowed_hash_algorithm != "sha256":
        errors.append("UNSUPPORTED_HASH_ALGORITHM")
    return not errors, tuple(errors)


def certify_timestamp(_policy: TimestampAuthorityPolicy, _token: bytes) -> bool:
    """Always fail closed until an independently reviewed RFC 3161 verifier exists."""
    return False
