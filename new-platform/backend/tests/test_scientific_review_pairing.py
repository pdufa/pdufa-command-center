from datetime import datetime, timezone
import hashlib
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from app import main
from app.scientific_review_submission import record_reviewer_submission
from app.scientific_review_pairing import review_pairing_status


def test_pairing_requires_distinct_subjects_and_valid_audit(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "pair.db"))
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
        for subject in ("a", "b"):
            session.add(main.ScientificReviewerAccount(
                google_subject=subject, verified_email=subject + "@example.org",
                role="reviewer", enabled=True, credentials_verified=True,
                created_at=datetime.now(timezone.utc)))
        session.commit()
    args = dict(nct_id="NCT02142738", question_id="safety_endpoint_taxonomy",
                source_sha256=hashlib.sha256(b"%PDF-1.4\\narchived-test-source\\n%%EOF").hexdigest(), decision="requires_review",
                attestation={"sourceLocator": "page 12", "reviewNote": "Uncertain",
                             "uncertaintyDisclosed": True})
    record_reviewer_submission(google_subject="a", **args)
    first = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert first["twoIndependentStatementsRecorded"] is False
    record_reviewer_submission(google_subject="b", **args)
    second = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert second["twoIndependentStatementsRecorded"] is True
    assert second["decisionsAgree"] is True
    assert second["clinicalIndependenceVerified"] is False
    assert second["scientificAdjudicationComplete"] is False
    assert second["mayPromoteScientificScore"] is False
    assert second["sourceByteIntegrityPassed"] is True
    assert second["currentlyAuthorizedReviewerCount"] == 2
    assert second["twoCurrentlyAuthorizedReviewers"] is True
    assert second["pairingTechnicalPreflightPassed"] is True

    # Current access checks must not rewrite the immutable historical review:
    # revoking an account leaves the signed statements recorded, but blocks
    # pairing eligibility until that account is authorized again.
    with Session(engine) as session:
        reviewer = session.get(main.ScientificReviewerAccount, "b")
        reviewer.enabled = False
        session.commit()
    revoked = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert revoked["twoIndependentStatementsRecorded"] is True
    assert revoked["currentlyAuthorizedReviewerCount"] == 1
    assert revoked["twoCurrentlyAuthorizedReviewers"] is False
    assert revoked["pairingTechnicalPreflightPassed"] is False
    assert revoked["mayPromoteScientificScore"] is False
    with Session(engine) as session:
        reviewer = session.get(main.ScientificReviewerAccount, "b")
        reviewer.enabled = True
        source = session.get(main.ScientificSourceDocument, "1" * 32)
        source.payload = b"%PDF-1.4\\nchanged-source\\n%%EOF"
        session.commit()
    corrupted = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert corrupted["twoIndependentStatementsRecorded"] is True
    assert corrupted["sourceByteIntegrityPassed"] is False
    assert corrupted["pairingTechnicalPreflightPassed"] is False
    assert corrupted["sourceContentIndependentlyVerified"] is False
    with Session(engine) as session:
        source = session.get(main.ScientificSourceDocument, "1" * 32)
        source.payload = pdf
        session.commit()
    restored = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert restored["sourceByteIntegrityPassed"] is True
    assert restored["pairingTechnicalPreflightPassed"] is True
    with Session(engine) as session:
        event = session.scalar(select(main.ScientificReviewAuditEvent))
        event.event_sha256 = "0" * 64
        session.commit()
    tampered = review_pairing_status(args["nct_id"], args["question_id"], args["source_sha256"])
    assert tampered["auditIntegrityPassed"] is False
    assert tampered["twoIndependentStatementsRecorded"] is False


def test_empty_pairing_never_passes_audit(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "empty_pair.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    result = review_pairing_status("NCT02142738", "safety_endpoint_taxonomy", "a" * 64)
    assert result["auditIntegrityPassed"] is False
    assert result["twoDistinctIdentityStatementsRecorded"] is False
    assert result["sourceByteIntegrityPassed"] is False
    assert result["currentlyAuthorizedReviewerCount"] == 0
    assert result["pairingTechnicalPreflightPassed"] is False
