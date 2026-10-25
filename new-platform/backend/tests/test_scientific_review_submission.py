from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import main
from app.scientific_review_submission import record_reviewer_submission


def setup_db(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "review.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    with Session(engine) as session:
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
        question_id="safety_endpoint_taxonomy", source_sha256="a" * 64,
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
