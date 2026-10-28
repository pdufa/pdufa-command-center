"""Read-only verification of stored reviewer submissions and audit envelopes."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import main
from .scientific_dual_review import audit_digest


def audit_readback(nct_id: str, question_id: str, *, max_events: int = 100) -> dict:
    """Recompute stored digests and report integrity, never adjudicate evidence."""
    from .scientific_review_submission import NCT_RE, QUESTION_RE
    if not isinstance(nct_id, str) or not NCT_RE.fullmatch(nct_id):
        raise ValueError("Valid NCT trial required")
    if not isinstance(question_id, str) or not QUESTION_RE.fullmatch(question_id):
        raise ValueError("Valid question ID required")
    with Session(main.ENGINE) as session:
        events = session.scalars(select(main.ScientificReviewAuditEvent).where(
            main.ScientificReviewAuditEvent.nct_id == nct_id,
            main.ScientificReviewAuditEvent.question_id == question_id,
        ).order_by(main.ScientificReviewAuditEvent.recorded_at,
                   main.ScientificReviewAuditEvent.id).limit(max_events + 1)).all()
        submissions = session.scalars(select(main.ScientificReviewSubmission).where(
            main.ScientificReviewSubmission.nct_id == nct_id,
            main.ScientificReviewSubmission.question_id == question_id,
        )).all()
        truncated = len(events) > max_events
        results = []
        for event in events[:max_events]:
            payload = event.event_payload
            try:
                event_digest_valid = (event.event_sha256 == audit_digest(payload))
            except (ValueError, TypeError, OverflowError):
                event_digest_valid = False
            submission = session.get(main.ScientificReviewSubmission,
                                     payload.get("submissionId", "") if isinstance(payload, dict) else "")
            submission_valid = False
            if submission is not None and isinstance(payload, dict):
                statement = {
                    "nctId": submission.nct_id, "questionId": submission.question_id,
                    "sourceSha256": submission.source_sha256,
                    "googleSubject": submission.google_subject,
                    "decision": submission.decision,
                    "attestation": submission.attestation,
                }
                try:
                    statement_valid = submission.content_sha256 == audit_digest(statement)
                except (ValueError, TypeError, OverflowError):
                    statement_valid = False
                submission_valid = (
                    statement_valid
                    and submission.content_sha256 == payload.get("contentSha256")
                    and submission.google_subject == event.google_subject
                    and submission.nct_id == event.nct_id
                    and submission.question_id == event.question_id
                )
            results.append({
                "eventId": event.id, "eventType": event.event_type,
                "submissionId": payload.get("submissionId") if isinstance(payload, dict) else None,
                "integrityVerified": event_digest_valid and submission_valid,
            })
        referenced_ids = [event.event_payload.get("submissionId")
                          for event in events
                          if isinstance(event.event_payload, dict)
                          and event.event_type == "review_statement_submitted"]
        expected_ids = {submission.id for submission in submissions}
        history_complete = (not truncated
                            and len(referenced_ids) == len(expected_ids)
                            and set(referenced_ids) == expected_ids)
    return {
        "recordedSubmissionCount": len(submissions),
        "auditHistoryComplete": history_complete,
        "hasRecordedReview": bool(submissions),
        "nctId": nct_id, "questionId": question_id,
        "events": results, "truncated": truncated,
        "integrityVerified": history_complete and bool(submissions) and all(x["integrityVerified"] for x in results),
        "independentSourceVerified": False, "adjudicated": False,
        "scientificScore": None,
    }
