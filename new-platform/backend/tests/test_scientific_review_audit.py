from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import main
from app.scientific_review_audit import audit_readback
from app.scientific_review_submission import record_reviewer_submission


def test_audit_readback_detects_modified_statement(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "audit.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    with Session(engine) as session:
        session.add(main.ScientificReviewerAccount(
            google_subject="reviewer-a", verified_email="a@example.org",
            role="reviewer", enabled=True, credentials_verified=True,
            created_at=datetime.now(timezone.utc)))
        session.commit()
    record_reviewer_submission(
        google_subject="reviewer-a", nct_id="NCT02142738",
        question_id="safety_endpoint_taxonomy", source_sha256="a" * 64,
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
