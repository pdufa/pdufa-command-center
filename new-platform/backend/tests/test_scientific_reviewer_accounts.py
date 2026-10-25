import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main
from app.scientific_reviewer_accounts import reviewer_access_preflight


def test_missing_account_never_authorized(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "reviewers.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    result = reviewer_access_preflight("unknown-google-sub")
    assert result["registered"] is False
    assert result["roleAuthorized"] is False
    assert result["maySignOff"] is False


def test_disabled_account_never_authorized(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    engine = create_engine("sqlite:///" + str(tmp_path / "reviewers.db"))
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    with Session(engine) as session:
        session.add(main.ScientificReviewerAccount(
            google_subject="google-sub", verified_email="r@example.org",
            role="reviewer", credentials_verified=True, enabled=False,
            created_at=datetime.now(timezone.utc)))
        session.commit()
    result = reviewer_access_preflight("google-sub")
    assert result["registered"] is True
    assert result["roleAuthorized"] is False
    assert result["maySignOff"] is False


@pytest.mark.parametrize("subject", ["", None, "x" * 256])
def test_invalid_subject_rejected(subject):
    with pytest.raises(ValueError):
        reviewer_access_preflight(subject)
