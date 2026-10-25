from datetime import datetime, timezone
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app import main
from app.scientific_review_submission import record_reviewer_submission
from app.scientific_review_pairing import review_pairing_status


def test_pairing_requires_distinct_subjects_and_valid_audit(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "pair.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    with Session(engine) as session:
        for subject in ("a", "b"):
            session.add(main.ScientificReviewerAccount(
                google_subject=subject, verified_email=subject + "@example.org",
                role="reviewer", enabled=True, credentials_verified=True,
                created_at=datetime.now(timezone.utc)))
        session.commit()
    args = dict(nct_id="NCT02142738", question_id="safety_endpoint_taxonomy",
                source_sha256="a" * 64, decision="requires_review",
                attestation={"sourceLocator": "page 12", "reviewNote": "Uncertain",
                             "uncertaintyDisclosed": True})
    record_reviewer_submission(google_subject="a", **args)
    first = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert first["twoIndependentStatementsRecorded"] is False
    record_reviewer_submission(google_subject="b", **args)
    second = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert second["twoIndependentStatementsRecorded"] is True
    assert second["decisionsAgree"] is True
    assert second["scientificAdjudicationComplete"] is False
    assert second["mayPromoteScientificScore"] is False
    with Session(engine) as session:
        event = session.scalar(select(main.ScientificReviewAuditEvent))
        event.event_sha256 = "0" * 64
        session.commit()
    tampered = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert tampered["auditIntegrityPassed"] is False
    assert tampered["twoIndependentStatementsRecorded"] is False
