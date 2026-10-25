"""Transactional reviewer submission recorder. No scientific score promotion."""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import main
from .scientific_dual_review import audit_digest

NCT_RE = re.compile(r"^NCT[0-9]{8}$")
QUESTION_RE = re.compile(r"^[a-z][a-z0-9_]{2,69}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = {"requires_review", "supports_reconciliation", "disputes_reconciliation"}


def record_reviewer_submission(*, google_subject: str, nct_id: str,
                               question_id: str, source_sha256: str,
                               decision: str, attestation: dict) -> dict:
    """Write an audited immutable statement only for provisioned verified reviewers.

    Must be called exclusively after server-side Google token verification.
    Caller must not treat a reviewer assertion as independent source verification.
    """
    if (not isinstance(google_subject, str) or not google_subject
            or len(google_subject) > 255 or not NCT_RE.fullmatch(nct_id)
            or not QUESTION_RE.fullmatch(question_id)
            or not SHA_RE.fullmatch(source_sha256)
            or decision not in DECISIONS or not isinstance(attestation, dict)):
        raise ValueError("Invalid scientific review submission")
    if set(attestation) != {"sourceLocator", "reviewNote", "uncertaintyDisclosed"}:
        raise ValueError("Required review attestation fields missing")
    if (not isinstance(attestation["sourceLocator"], str)
            or not 1 <= len(attestation["sourceLocator"]) <= 200
            or not isinstance(attestation["reviewNote"], str)
            or not 1 <= len(attestation["reviewNote"]) <= 1500
            or attestation["uncertaintyDisclosed"] is not True):
        raise ValueError("Review statement must disclose uncertainty")
    from .scientific_reconciliation_worklist import reconciliation_worklist
    checks = reconciliation_worklist(nct_id)["checks"]
    if question_id not in {check["id"] for check in checks}:
        raise ValueError("Question not present in server reconciliation worklist")
    with Session(main.ENGINE) as session:
        # A client-provided digest is never sufficient to establish source custody.
        source = session.scalar(select(main.ScientificSourceDocument).where(
            main.ScientificSourceDocument.nct_id == nct_id,
            main.ScientificSourceDocument.sha256 == source_sha256,
        ))
        if source is None:
            raise ValueError("Source document is not archived for this trial")
        from .scientific_source_documents import _capture_meta
        _capture_meta(source)  # Checks archived PDF bytes and metadata digest.
        allowed_urls = next(check["sourceUrls"] for check in checks
                            if check["id"] == question_id)
        if source.source_url not in allowed_urls:
            raise ValueError("Archived source is not linked to this review question")
        account = session.get(main.ScientificReviewerAccount, google_subject)
        if (account is None or not account.enabled
                or not account.credentials_verified
                or account.role not in ("reviewer", "second_reviewer")):
            raise PermissionError("Reviewer not authorized")
        payload = {
            "nctId": nct_id, "questionId": question_id,
            "sourceSha256": source_sha256, "googleSubject": google_subject,
            "decision": decision, "attestation": attestation,
        }
        digest = audit_digest(payload)
        submission_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        session.add(main.ScientificReviewSubmission(
            id=submission_id, nct_id=nct_id, question_id=question_id,
            source_sha256=source_sha256, google_subject=google_subject,
            decision=decision, attestation=attestation,
            content_sha256=digest, submitted_at=now))
        session.add(main.ScientificReviewAuditEvent(
            id=uuid.uuid4().hex, nct_id=nct_id, question_id=question_id,
            google_subject=google_subject, event_type="review_statement_submitted",
            event_payload={"submissionId": submission_id, "contentSha256": digest},
            event_sha256=audit_digest({"submissionId": submission_id,
                                       "contentSha256": digest}), recorded_at=now))
        try:
            session.commit()
        except IntegrityError as exc:
            session.rollback()
            raise ValueError("Duplicate reviewer statement for this source") from exc
        rows = session.scalars(select(main.ScientificReviewSubmission).where(
            main.ScientificReviewSubmission.nct_id == nct_id,
            main.ScientificReviewSubmission.question_id == question_id,
            main.ScientificReviewSubmission.source_sha256 == source_sha256,
            main.ScientificReviewSubmission.decision == decision,
        )).all()
        distinct_subjects = {row.google_subject for row in rows}
    return {
        "submissionId": submission_id,
        "auditRecorded": True,
        "distinctReviewerCount": len(distinct_subjects),
        "twoIndependentStatementsRecorded": len(distinct_subjects) >= 2,
        "sourceContentIndependentlyVerified": False,
        "adjudicated": False,
        "scientificScore": None,
        "mayPromoteReadiness": False,
    }
