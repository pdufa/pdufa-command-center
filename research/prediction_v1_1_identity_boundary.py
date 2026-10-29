"""Retired claim-to-principal shortcut; HTTP identity requires signature verification.

A caller-controlled boolean can never establish cryptographic authentication.
The isolated research API resolves verified issuer/subject pairs against its
server-owned directory; JWT role and program claims are not used as grants.
"""

class ResearchIdentityUnavailable(RuntimeError):
    pass


def principal_from_verified_claims(claims, *, verified_by_provider=False):
    """Reject the legacy shortcut even when its old boolean flag is supplied."""
    raise ResearchIdentityUnavailable(
        "Claim dictionaries and verification flags cannot create trusted identities; "
        "use cryptographic verification and the server-owned principal directory")
