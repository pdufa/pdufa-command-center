from fastapi.testclient import TestClient
from app import main


def test_google_reviewer_endpoint_requires_token():
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/reviewer/me")
    assert response.status_code == 401


def test_google_reviewer_endpoint_denies_unprovisioned_subject(monkeypatch):
    from app import scientific_google_identity, scientific_reviewer_accounts
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda token: {"providerSubject": "unknown-google-sub",
                                       "verifiedEmail": "unprovisioned@example.org"})
    monkeypatch.setattr(scientific_reviewer_accounts, "reviewer_access_preflight",
                        lambda subject: {"roleAuthorized": False,
                                         "credentialsVerified": False})
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/reviewer/me",
                              headers={"Authorization": "Bearer fake-test-token"})
    assert response.status_code == 403


def test_google_reviewer_endpoint_does_not_authorize_signoff(monkeypatch):
    from app import scientific_google_identity, scientific_reviewer_accounts
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda token: {"providerSubject": "test-sub",
                                       "verifiedEmail": "reviewer@example.org"})
    monkeypatch.setattr(scientific_reviewer_accounts, "reviewer_access_preflight",
                        lambda subject: {"roleAuthorized": True,
                                         "credentialsVerified": True})
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/reviewer/me",
                              headers={"Authorization": "Bearer fake-test-token"})
    assert response.status_code == 200
    assert response.json()["maySignOff"] is False
