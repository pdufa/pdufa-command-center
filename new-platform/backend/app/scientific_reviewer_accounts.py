"""Read-only Google reviewer authorization; no self-registration or signoff."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main


def reviewer_access_preflight(google_subject: str, verified_email: str | None = None) -> dict:
    """Only server-verified Google subjects may be looked up."""
    if not isinstance(google_subject, str) or not 1 <= len(google_subject) <= 255:
        raise ValueError("Verified Google subject required")
    if verified_email is not None and (not isinstance(verified_email, str) or not verified_email):
        raise ValueError("Verified email required")
    with Session(main.ENGINE) as session:
        account = session.get(main.ScientificReviewerAccount, google_subject)
        if account is None:
            return {
                "registered": False, "roleAuthorized": False,
                "credentialsVerified": False, "maySignOff": False,
                "status": "requires_admin_provisioning",
            }
        # An authorized review role always requires BOTH the verified Google
        # subject and independently verified Google email to match the allowlist.
        email_matches = bool(verified_email and
                             account.verified_email.casefold() == verified_email.casefold())
        allowed = bool(email_matches and account.enabled and account.credentials_verified
                       and account.role in ("reviewer", "second_reviewer"))
        return {
            "registered": True,
            "roleAuthorized": allowed,
            "credentialsVerified": bool(account.credentials_verified),
            "maySignOff": False,
            "status": "role_preflight_only" if allowed else "review_access_blocked",
        }



def reviewer_setup_summary() -> dict:
    """Operator-only aggregate diagnostic, not a reviewer provisioning action.

    Do not include private reviewer names, Google subjects or email addresses.
    Each person must present separately verified Google identity and have
    credentials independently validated before audited statements are allowed.
    """
    with Session(main.ENGINE) as session:
        rows = session.scalars(select(main.ScientificReviewerAccount)).all()
    supported = {"reviewer", "second_reviewer"}
    eligible = [
        account for account in rows
        if account.role in supported and account.enabled and account.credentials_verified
    ]
    distinct = {account.google_subject for account in eligible}
    return {
        "status": "reviewer_infrastructure_ready" if eligible else "awaiting_reviewer_provisioning",
        "totalProvisioningRecords": len(rows),
        "activeCredentialVerifiedIdentities": len(distinct),
        "pendingOrDisabledIdentities": len(rows) - len(eligible),
        "requiredDistinctReviewerIdentities": 2,
        "dualReviewIdentityCountMet": len(distinct) >= 2,
        "onboardingMode": "admin_provisioned_only",
        "operatorMayActAsIndependentReviewer": False,
        "selfRegistrationAllowed": False,
        "qualificationsAutomaticallyVerified": False,
        "maySignOff": False,
        "independentScientificAdjudicationImplemented": False,
        "note": (
            "Verified Google identities and independently checked credentials "
            "must be provisioned by an authorized administrator. Even two "
            "reviewer statements do not independently adjudicate science."
        ),
    }
