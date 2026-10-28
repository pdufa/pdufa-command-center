from datetime import datetime, timezone
import hashlib

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import main
from app.scientific_review_audit import audit_readback
from app.scientific_review_submission import record_reviewer_submission


def test_audit_readback_detects_modified_statement(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "audit.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    from app.scientific_source_documents import CAPTURE_STATUS, _metadata_hash
    from app.scientific_reconciliation_worklist import REGISTRY
    pdf = b"%PDF-1.4\\narchived-test-source\\n%%EOF"
    digest = hashlib.sha256(pdf).hexdigest()
    with Session(engine) as session:
        source = main.ScientificSourceDocument(
            id="1" * 32, nct_id="NCT02142738", gate_id="published_results",
            source_url=REGISTRY, source_type="protocol", filename="source.pdf",
            captured_by="test", captured_at=datetime.now(timezone.utc),
            sha256=digest, byte_length=len(pdf), payload=pdf,
            capture_status=CAPTURE_STATUS, manifest_sha256="0" * 64)
        source.manifest_sha256 = _metadata_hash(source)
        session.add(source)
        session.commit()
    with Session(engine) as session:
        session.add(main.ScientificReviewerAccount(
            google_subject="reviewer-a", verified_email="a@example.org",
            role="reviewer", enabled=True, credentials_verified=True,
            created_at=datetime.now(timezone.utc)))
        session.commit()
    record_reviewer_submission(
        google_subject="reviewer-a", nct_id="NCT02142738",
        question_id="safety_endpoint_taxonomy", source_sha256=hashlib.sha256(b"%PDF-1.4\\narchived-test-source\\n%%EOF").hexdigest(),
        decision="requires_review", attestation={
            "sourceLocator": "page 2", "reviewNote": "Uncertainty remains",
            "uncertaintyDisclosed": True})
    result = audit_readback("NCT02142738", "safety_endpoint_taxonomy")
    assert result["integrityVerified"] is True
    assert result["adjudicated"] is False
    with Session(engine) as session:
        item = session.scalar(select(main.ScientificReviewSubmission))
        item.decision = "supports_reconciliation"
        session.commit()
    result = audit_readback("NCT02142738", "safety_endpoint_taxonomy")
    assert result["integrityVerified"] is False
    assert result["events"][0]["integrityVerified"] is False


def test_empty_audit_is_not_verified(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "empty.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    result = audit_readback("NCT02142738", "safety_endpoint_taxonomy")
    assert result["hasRecordedReview"] is False
    assert result["integrityVerified"] is False


def test_deleted_audit_event_fails_completeness(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "missing.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    with Session(engine) as session:
        session.add(main.ScientificReviewSubmission(
            id="f" * 32, nct_id="NCT02142738",
            question_id="safety_endpoint_taxonomy", source_sha256="a" * 64,
            google_subject="reviewer-a", decision="requires_review",
            attestation={}, content_sha256="b" * 64,
            submitted_at=datetime.now(timezone.utc)))
        session.commit()
    result = audit_readback("NCT02142738", "safety_endpoint_taxonomy")
    assert result["recordedSubmissionCount"] == 1
    assert result["auditHistoryComplete"] is False
    assert result["integrityVerified"] is False
