"""Operator-only nomination queue. No email dispatch, role grants or review access.

A nomination is a candidate record, not a verified reviewer. Separately
verified Google subject, email, professional qualifications, independence and
administrator authorization are prerequisites of another controlled process.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main

_NOMINATION_STATUS = "pending_independent_verification"
_EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+\-/=?^_`{|}~]+@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$")
_ALLOWED_SPECIALTIES = frozenset({
    "clinical_oncology", "biostatistics", "drug_safety", "regulatory_science"
})


class DuplicateNomination(Exception):
    """A candidate is already in the queue."""


def _normalized_candidate_email(value: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise ValueError("Enter an unpadded Google email address")
    if not 5 <= len(value) <= 320 or not _EMAIL_RE.fullmatch(value) or ".." in value:
        raise ValueError("Enter a valid candidate Google email address")
    domain = value.rsplit("@", 1)[-1]
    if "." not in domain or domain.startswith(".") or domain.endswith("."):
        raise ValueError("Candidate email must have a valid domain")
    return value.casefold()


def _public_candidate(row: main.ScientificReviewerNomination) -> dict:
    return {
        "id": row.id,
        "candidateEmail": row.candidate_email,
        "displayName": row.display_name,
        "specialty": row.specialty,
        "qualificationsNote": row.qualifications_note,
        "status": row.nomination_status,
        "nominatedAt": row.nominated_at.isoformat(),
        "googleIdentityVerified": False,
        "credentialsVerified": False,
        "independenceVerified": False,
        "invitationSent": False,
        "reviewerAccessGranted": False,
        "maySubmitAuditedStatements": False,
        "maySignOff": False,
    }


def nominate_reviewer(
    *, candidate_email: str, display_name: str, specialty: str,
    qualifications_note: str = ""
) -> dict:
    email = _normalized_candidate_email(candidate_email)
    if specialty not in _ALLOWED_SPECIALTIES:
        raise ValueError("Unsupported scientific review specialty")
    if not isinstance(display_name, str) or len(display_name) > 160:
        raise ValueError("Candidate name too long")
    if not isinstance(qualifications_note, str) or len(qualifications_note) > 1200:
        raise ValueError("Qualification note too long")
    owner = (main.os.getenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL") or "").strip()
    if owner and email == owner.casefold():
        raise ValueError("Operator cannot nominate their own Google account as independent reviewer")

    with Session(main.ENGINE) as session:
        existing = session.scalar(select(main.ScientificReviewerNomination).where(
            main.ScientificReviewerNomination.candidate_email == email))
        if existing is not None:
            raise DuplicateNomination("Candidate already nominated")
        item = main.ScientificReviewerNomination(
            id=secrets.token_hex(16), candidate_email=email,
            display_name=display_name.strip(), specialty=specialty,
            qualifications_note=qualifications_note.strip(),
            nomination_status=_NOMINATION_STATUS,
            nominated_at=datetime.now(timezone.utc),
        )
        session.add(item)
        session.commit()
        return _public_candidate(item)


def list_nominations() -> dict:
    with Session(main.ENGINE) as session:
        rows = session.scalars(
            select(main.ScientificReviewerNomination)
            .order_by(main.ScientificReviewerNomination.nominated_at.desc())
            .limit(100)
        ).all()
    return {
        "nominations": [_public_candidate(row) for row in rows],
        "listedCount": len(rows),
        "operatorOnly": True,
        "selfRegistrationEnabled": False,
        "automaticCredentialsVerification": False,
        "invitationsSent": False,
        "reviewerAccessGrantedByNomination": False,
        "maySignOff": False,
        "note": (
            "Nomination is only a pending screening record. It has no reviewer "
            "Google subject, role, enabled account or scientific permissions."
        ),
    }
