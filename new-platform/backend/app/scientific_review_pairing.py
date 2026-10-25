"""Read-only independent reviewer pairing, not scientific adjudication."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main
from .scientific_review_submission import NCT_RE, QUESTION_RE, SHA_RE
from .scientific_dual_review import audit_digest


def review_pairing_status(nct_id: str, question_id: str, source_sha256: str) -> dict:
    if (not isinstance(nct_id, str) or not NCT_RE.fullmatch(nct_id)
            or not isinstance(question_id, str) or not QUESTION_RE.fullmatch(question_id)
            or not isinstance(source_sha256, str) or not SHA_RE.fullmatch(source_sha256)):
        raise ValueError("Exact trial, question and source hash required")
    with Session(main.ENGINE) as session:
        rows = session.scalars(select(main.ScientificReviewSubmission).where(
            main.ScientificReviewSubmission.nct_id == nct_id,
            main.ScientificReviewSubmission.question_id == question_id,
            main.ScientificReviewSubmission.source_sha256 == source_sha256,
        )).all()
        valid = []
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
            if (audit_digest(payload) == row.content_sha256
                    and any(isinstance(e.event_payload, dict)
                            and e.event_payload.get("submissionId") == row.id
                            and e.event_payload.get("contentSha256") == row.content_sha256
                            and audit_digest(e.event_payload) == e.event_sha256
                            for e in events)):
                valid.append(row)
        subjects = {row.google_subject for row in valid}
        decisions = {row.decision for row in valid}
    return {
        "nctId": nct_id, "questionId": question_id, "sourceSha256": source_sha256,
        "recordedStatements": len(rows),
        "integrityVerifiedStatements": len(valid),
        "distinctReviewerCount": len(subjects),
        "twoIndependentStatementsRecorded": len(subjects) >= 2,
        "decisionsAgree": len(subjects) >= 2 and len(decisions) == 1,
        "auditIntegrityPassed": len(rows) == len(valid),
        "sourceContentIndependentlyVerified": False,
        "qualificationsIndependentlyAdjudicated": False,
        "formalSecondPersonSignoff": False,
        "scientificAdjudicationComplete": False,
        "mayPromoteScientificScore": False,
    }
