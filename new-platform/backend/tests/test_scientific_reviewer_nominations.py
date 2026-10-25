"""Operator candidate nominations never authorize independent scientific review."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, scientific_google_identity
from app.scientific_reviewer_nominations import _normalized_candidate_email

HEADERS = {"Authorization": "Bearer mock-signed-Google-token"}
PATH = "/api/scientific-assessment/operator/reviewer-nominations"
NOMINATION = {
    "candidateEmail": "Scientist.Independent@Example.org",
    "displayName": "Independent Scientific Reviewer",
    "specialty": "biostatistics",
    "qualificationsNote": "Biostatistics experience; registration and independence require verification",
    "nominationOnlyAcknowledged": True,
}


@pytest.fixture
def environment(monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False},
    )
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/reviews")
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda token: {"providerSubject": "operator-google-sub",
                                       "verifiedEmail": "owner@example.org"})
    yield TestClient(main.app), engine
    engine.dispose()


def test_reviewer_nomination_requires_operator_google_identity(environment, monkeypatch):
    client, engine = environment
    assert client.get(PATH).status_code == 401
    assert client.post(PATH, json=NOMINATION).status_code == 401
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"providerSubject": "reviewer-google-sub",
                                   "verifiedEmail": "other@example.org"})
    assert client.get(PATH, headers=HEADERS).status_code == 403
    assert client.post(PATH, headers=HEADERS, json=NOMINATION).status_code == 403
    with Session(engine) as session:
        assert session.scalars(select(main.ScientificReviewerNomination)).first() is None
        assert session.scalars(select(main.ScientificReviewerAccount)).first() is None


def test_pending_nomination_does_not_invite_provision_or_authorize(environment):
    client, engine = environment
    res = client.post(PATH, headers=HEADERS, json=NOMINATION)
    assert res.status_code == 201, res.text
    receipt = res.json()
    assert receipt["candidateEmail"] == "scientist.independent@example.org"
    assert receipt["status"] == "pending_independent_verification"
    assert receipt["googleIdentityVerified"] is False
    assert receipt["credentialsVerified"] is False
    assert receipt["independenceVerified"] is False
    assert receipt["invitationSent"] is False
    assert receipt["reviewerAccessGranted"] is False
    assert receipt["maySubmitAuditedStatements"] is False
    assert receipt["maySignOff"] is False
    assert "no-store" in res.headers["cache-control"]

    listing = client.get(PATH, headers=HEADERS)
    assert listing.status_code == 200
    assert listing.json()["listedCount"] == 1
    assert listing.json()["nominations"][0]["candidateEmail"] == receipt["candidateEmail"]
    assert listing.json()["operatorOnly"] is True
    assert listing.json()["selfRegistrationEnabled"] is False
    assert listing.json()["invitationsSent"] is False
    assert listing.json()["reviewerAccessGrantedByNomination"] is False
    assert "no-store" in listing.headers["cache-control"]

    with Session(engine) as session:
        assert session.scalar(select(main.ScientificReviewerNomination)) is not None
        assert session.scalar(select(main.ScientificReviewerAccount)) is None
        assert session.scalar(select(main.ScientificReviewSubmission)) is None
        assert session.scalar(select(main.ScientificReviewAuditEvent)) is None


def test_nomination_duplicate_is_case_insensitive_and_fails_closed(environment):
    client, engine = environment
    assert client.post(PATH, headers=HEADERS, json=NOMINATION).status_code == 201
    duplicated = {**NOMINATION, "candidateEmail": "SCIENTIST.INDEPENDENT@example.org"}
    assert client.post(PATH, headers=HEADERS, json=duplicated).status_code == 409
    with Session(engine) as session:
        assert len(session.scalars(select(main.ScientificReviewerNomination)).all()) == 1


@pytest.mark.parametrize("invalid", [
    {"candidateEmail": "owner@example.org"},
    {"candidateEmail": "OWNER@EXAMPLE.ORG"},
    {"candidateEmail": " outsider@example.org"},
    {"candidateEmail": "outsider@example.org "},
    {"candidateEmail": "not-a-google-email"},
    {"candidateEmail": "a@b..example"},
    {"specialty": "unverified_admin"},
    {"nominationOnlyAcknowledged": False},
    {"credentialsVerified": True},
    {"enabled": True},
    {"role": "second_reviewer"},
    {"maySignOff": True},
    {"googleSubject": "fake-subject"},
])
def test_invalid_nomination_cannot_be_saved_or_claim_permissions(environment, invalid):
    client, engine = environment
    payload = {**NOMINATION, **invalid}
    response = client.post(PATH, headers=HEADERS, json=payload)
    assert response.status_code == 422, (invalid, response.status_code, response.text)
    with Session(engine) as session:
        assert session.scalars(select(main.ScientificReviewerNomination)).first() is None
        assert session.scalars(select(main.ScientificReviewerAccount)).first() is None


def test_wrong_render_service_or_storage_refuses_nomination(environment, monkeypatch):
    client, engine = environment
    monkeypatch.setenv("RENDER_SERVICE_ID", "production-unsafe-service")
    assert client.post(PATH, headers=HEADERS, json=NOMINATION).status_code == 403
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setattr(main, "_DB_STATE", {"available": False, "reason": "DISCONNECTED"})
    assert client.post(PATH, headers=HEADERS, json=NOMINATION).status_code == 503
    with Session(engine) as session:
        assert session.scalars(select(main.ScientificReviewerNomination)).first() is None


def test_role_counts_are_not_inflated_by_pending_candidate(environment):
    client, engine = environment
    assert client.post(PATH, headers=HEADERS, json=NOMINATION).status_code == 201
    status = client.get("/api/scientific-assessment/operator/reviewer-setup", headers=HEADERS)
    assert status.status_code == 200
    result = status.json()
    assert result["activeCredentialVerifiedIdentities"] == 0
    assert result["dualReviewIdentityCountMet"] is False
    assert result["totalProvisioningRecords"] == 0
    assert result["maySignOff"] is False
    with Session(engine) as session:
        assert session.scalar(select(main.ScientificReviewSubmission)) is None


def test_email_normalization_rejects_invalid_domain_and_whitespace():
    assert _normalized_candidate_email("FIRST.LAST+science@EXAMPLE.ORG") == "first.last+science@example.org"
    for invalid in ("no-domain@", "a@b", "someone@-bad-domain.com", "a@b..com",
                    " space@example.org", "contains space@example.org", ""):
        with pytest.raises(ValueError):
            _normalized_candidate_email(invalid)
