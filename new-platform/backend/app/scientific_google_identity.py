"""Google identity verification boundary for isolated scientific reviewer sign-in.

This module does not grant clinical credentials, reviewer roles, independent
adjudication, or permission to promote scientific scores. No token is logged.
"""
from __future__ import annotations

import os
from collections.abc import Mapping

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


def verified_google_identity(token: str) -> dict[str, str]:
    """Verify Google signature, issuer, audience, expiration and email status.

    The Google client ID must be configured separately in isolated Render.
    Identity alone never authorizes reviewer sign-off or clinical adjudication.
    """
    audience = os.getenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID", "").strip()
    if not audience:
        raise ValueError("Google scientific reviewer authentication not configured")
    if not isinstance(token, str) or not 20 <= len(token) <= 8192:
        raise ValueError("Google identity token required")
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token
    try:
        claims = id_token.verify_oauth2_token(token, Request(), audience=audience)
    except Exception as exc:
        raise ValueError("Google identity token verification failed") from exc
    return identity_from_verified_claims(claims, audience)


def identity_from_verified_claims(claims: Mapping, audience: str) -> dict[str, str]:
    """Apply extra fail-closed policy to cryptographically verified claims.

    Never call this helper on unverified client-provided JSON.
    """
    if not isinstance(claims, Mapping) or not audience:
        raise ValueError("Verified Google claims required")
    if claims.get("iss") not in GOOGLE_ISSUERS or claims.get("aud") != audience:
        raise ValueError("Google issuer or client audience mismatch")
    subject, email = claims.get("sub"), claims.get("email")
    if (not isinstance(subject, str) or not 1 <= len(subject) <= 255
            or not isinstance(email, str) or not 3 <= len(email) <= 320
            or claims.get("email_verified") is not True):
        raise ValueError("Verified Google subject and email required")
    return {
        "provider": "google",
        "providerSubject": subject,
        "verifiedEmail": email,
        "identityVerified": "true",
        "clinicalCredentialsVerified": "false",
        "reviewerRoleAuthorized": "false",
        "maySignOff": "false",
    }
