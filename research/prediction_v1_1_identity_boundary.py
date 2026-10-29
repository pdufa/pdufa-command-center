"""Identity-provider integration boundary for research. No live verifier exists."""
from research.prediction_v1_1_authorization import ResearchPrincipal

class ResearchIdentityUnavailable(RuntimeError):
    pass

def principal_from_verified_claims(claims, *, verified_by_provider=False):
    # This flag is NOT cryptographic verification. Never expose this function
    # to HTTP clients or use until trusted server middleware verifies identity.
    if not verified_by_provider:
        raise ResearchIdentityUnavailable("Trusted identity provider not connected")
    if not isinstance(claims, dict):
        raise ResearchIdentityUnavailable("Invalid claims")
    subject, roles, programs = claims.get("subject"), claims.get("roles"), claims.get("program_ids")
    if not isinstance(subject, str) or not subject.strip():
        raise ResearchIdentityUnavailable("Verified subject required")
    if not isinstance(roles, (set, frozenset)) or not all(isinstance(x,str) for x in roles):
        raise ResearchIdentityUnavailable("Server-owned roles required")
    if not isinstance(programs, (set, frozenset)) or not all(isinstance(x,str) for x in programs):
        raise ResearchIdentityUnavailable("Server-owned program grants required")
    return ResearchPrincipal(subject, frozenset(roles), frozenset(programs))
