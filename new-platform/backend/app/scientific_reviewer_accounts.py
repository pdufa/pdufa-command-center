"""Read-only Google reviewer authorization; no self-registration or signoff."""
from __future__ import annotations

from sqlalchemy.orm import Session

from . import main


def reviewer_access_preflight(google_subject: str) -> dict:
    """Only server-verified Google subjects may be looked up."""
    if not isinstance(google_subject, str) or not 1 <= len(google_subject) <= 255:
        raise ValueError("Verified Google subject required")
    with Session(main.ENGINE) as session:
        account = session.get(main.ScientificReviewerAccount, google_subject)
        if account is None:
            return {
                "registered": False, "roleAuthorized": False,
                "credentialsVerified": False, "maySignOff": False,
                "status": "requires_admin_provisioning",
            }
        allowed = bool(account.enabled and account.credentials_verified
                       and account.role in ("reviewer", "second_reviewer"))
        return {
            "registered": True,
            "roleAuthorized": allowed,
            "credentialsVerified": bool(account.credentials_verified),
            "maySignOff": False,
            "status": "role_preflight_only" if allowed else "review_access_blocked",
        }
