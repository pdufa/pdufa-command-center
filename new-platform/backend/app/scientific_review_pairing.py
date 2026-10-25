"""Read-only independent reviewer pairing, not scientific adjudication."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main
from .scientific_review_submission import NCT_RE, QUESTION_RE, SHA_RE
from .scientific_dual_review import audit_digest
from .scientific_source_documents import _capture_meta


def review_pairing_status(nct_id: str, question_id: str, source_sha256: str) -> dict:
    if (not isinstance(nct_id, str) or not NCT_RE.fullmatch(nct_id)
            or not isinstance(question_id, str) or not QUESTION_RE.fullmatch(question_id)
            or not isinstance(source_sha256, str) or not SHA_RE.fullmatch(source_sha256)):
        raise ValueError("Exact trial, question and source hash required")
    with Session(main.ENGINE) as session:
        # The historical statement archive is not enough to make a pairing
        # currently reviewable: the exact original PDF bytes may be corrupted
        # and either reviewer may have been disabled since submitting.
        source = session.scalar(select(main.ScientificSourceDocument).where(
            main.ScientificSourceDocument.nct_id == nct_id,
            main.ScientificSourceDocument.sha256 == source_sha256,
        ))
        source_integrity = False
        if source is not None:
            try:
                _capture_meta(source)  # Validates bytes, SHA-256 and metadata.
                source_integrity = True
            except (ValueError, TypeError, OverflowError):
                pass
        rows = session.scalars(select(main.ScientificReviewSubmission).where(
            main.ScientificReviewSubmission.nct_id == nct_id,
            main.ScientificReviewSubmission.question_id == question_id,
            main.ScientificReviewSubmission.source_sha256 == source_sha256,
        )).all()
        valid = []
        currently_authorized_subjects = set()
        for row in rows:
            payload = {"nctId": row.nct_id, "questionId": row.question_id,
                       "sourceSha256": row.source_sha256,
                       "googleSubject": row.google_subject,
                       "decision": row.decision, "attestation": row.attestation}
            events = session.scalars(select(main.ScientificReviewAuditEvent).where(
                main.ScientificReviewAuditEvent.nct_id == nct_id,
                main.ScientificReviewAuditEvent.question_id == question_id,
                main.ScientificReviewAuditEvent.google_subject == row.google_subject,
                main.ScientificReviewAuditEvent.event_type == "review_statement_submitted",
            )).all()
            try:
                statement_valid = audit_digest(payload) == row.content_sha256
                matching_events = [
                    e for e in events
                    if isinstance(e.event_payload, dict)
                    and e.event_payload.get("submissionId") == row.id
                    and e.event_payload.get("contentSha256") == row.content_sha256
                    and audit_digest(e.event_payload) == e.event_sha256
                ]
            except (ValueError, TypeError, OverflowError):
                statement_valid, matching_events = False, []
            if statement_valid and len(matching_events) == 1:
                valid.append(row)
                account = session.get(main.ScientificReviewerAccount, row.google_subject)
                if (account is not None and account.enabled
                        and account.credentials_verified
                        and account.role in ("reviewer", "second_reviewer")):
                    currently_authorized_subjects.add(row.google_subject)
        subjects = {row.google_subject for row in valid}
        decisions = {row.decision for row in valid}
    history_integrity = bool(rows) and len(rows) == len(valid)
    two_active_reviewers = len(currently_authorized_subjects) >= 2
    return {
        "nctId": nct_id, "questionId": question_id, "sourceSha256": source_sha256,
        "recordedStatements": len(rows),
        "integrityVerifiedStatements": len(valid),
        "distinctReviewerCount": len(subjects),
        "twoIndependentStatementsRecorded": len(subjects) >= 2,
        "twoDistinctIdentityStatementsRecorded": len(subjects) >= 2,
        "clinicalIndependenceVerified": False,
        "decisionsAgree": len(subjects) >= 2 and len(decisions) == 1,
        "auditIntegrityPassed": history_integrity,
        "sourceByteIntegrityPassed": source_integrity,
        "currentlyAuthorizedReviewerCount": len(currently_authorized_subjects),
        "twoCurrentlyAuthorizedReviewers": two_active_reviewers,
        "pairingTechnicalPreflightPassed": (
            history_integrity and source_integrity and two_active_reviewers
            and len(decisions) == 1
        ),
        "sourceContentIndependentlyVerified": False,
        "qualificationsIndependentlyAdjudicated": False,
        "formalSecondPersonSignoff": False,
        "scientificAdjudicationComplete": False,
        "mayPromoteScientificScore": False,
    }
