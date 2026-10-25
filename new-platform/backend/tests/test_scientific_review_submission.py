from datetime import datetime, timezone
import hashlib

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import main
from app.scientific_review_submission import record_reviewer_submission


def setup_db(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "review.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    from app.scientific_source_documents import CAPTURE_STATUS, _metadata_hash
    from app.scientific_reconciliation_worklist import REGISTRY
    pdf = b"%PDF-1.4\\narchived-test-source"
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
        for subject in ("reviewer-a", "reviewer-b"):
            session.add(main.ScientificReviewerAccount(
                google_subject=subject, verified_email=subject + "@example.org",
                role="reviewer", enabled=True, credentials_verified=True,
                created_at=datetime.now(timezone.utc)))
        session.commit()
    return engine


def submit(subject, **overrides):
    kwargs = dict(
        google_subject=subject, nct_id="NCT02142738",
        question_id="safety_endpoint_taxonomy", source_sha256=hashlib.sha256(b"%PDF-1.4\\narchived-test-source").hexdigest(),
        decision="requires_review",
        attestation={"sourceLocator": "page 12", "reviewNote": "Requires reconciliation",
                     "uncertaintyDisclosed": True})
    kwargs.update(overrides)
    return record_reviewer_submission(**kwargs)


def test_two_independent_statements_audited_without_promoting_scores(monkeypatch, tmp_path):
    engine = setup_db(monkeypatch, tmp_path)
    first = submit("reviewer-a")
    second = submit("reviewer-b")
    assert first["distinctReviewerCount"] == 1
    assert second["distinctReviewerCount"] == 2
    assert second["twoIndependentStatementsRecorded"] is True
    assert second["mayPromoteReadiness"] is False
    assert second["scientificScore"] is None
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(main.ScientificReviewSubmission)) == 2
        assert session.scalar(select(func.count()).select_from(main.ScientificReviewAuditEvent)) == 2


def test_duplicate_reviewer_rejected_without_extra_audit(monkeypatch, tmp_path):
    engine = setup_db(monkeypatch, tmp_path)
    submit("reviewer-a")
    with pytest.raises(ValueError, match="Duplicate"):
        submit("reviewer-a")
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(main.ScientificReviewAuditEvent)) == 1


def test_unknown_reviewer_denied(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    with pytest.raises(PermissionError):
        submit("unknown")


def test_uncertainty_disclosure_required(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError):
        submit("reviewer-a", attestation={"sourceLocator": "page 1",
               "reviewNote": "Note", "uncertaintyDisclosed": False})


def test_unknown_question_and_source_rejected(monkeypatch, tmp_path):
    engine = setup_db(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="Question not present"):
        submit("reviewer-a", question_id="unknown_question")
    with pytest.raises(ValueError, match="not archived"):
        submit("reviewer-a", source_sha256="a" * 64)
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(main.ScientificReviewSubmission)) == 0
