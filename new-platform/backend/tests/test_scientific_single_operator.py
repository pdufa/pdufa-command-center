"""The single operator login is not a substitute for independent review."""
from fastapi.testclient import TestClient

from app import main


def test_single_operator_requires_config(monkeypatch):
    monkeypatch.delenv("PDUFA_SCIENTIFIC_ACCESS_MODE", raising=False)
    monkeypatch.delenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", raising=False)
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 503


def test_single_operator_requires_verified_google_token(monkeypatch):
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me")
    assert r.status_code == 401


def test_single_operator_rejects_other_google_account(monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "someoneelse@example.org",
                                   "providerSubject": "another-google-sub"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 403


def test_single_operator_cannot_sign_off_or_promote_score(monkeypatch):
    from app import scientific_google_identity
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    monkeypatch.setattr(scientific_google_identity, "verified_google_identity",
                        lambda _: {"verifiedEmail": "OWNER@example.org",
                                   "providerSubject": "approved-google-sub"})
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/operator/me",
                       headers={"Authorization": "Bearer fake"})
    assert r.status_code == 200
    payload = r.json()
    assert payload["role"] == "operator"
    assert payload["identityVerified"] is True
    assert payload["maySubmitScientificReview"] is False
    assert payload["maySignOff"] is False
    assert payload["independentlyVerified"] is False
    assert payload["mayPromoteScientificScore"] is False
    assert payload["reviewerProvisioningRequired"] is True


def test_auth_status_exposes_mode_not_email(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID",
                       "example-client.apps.googleusercontent.com")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_ACCESS_MODE", "single_operator")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_SINGLE_OPERATOR_EMAIL", "owner@example.org")
    with TestClient(main.app) as client:
        r = client.get("/api/scientific-assessment/reviewer/auth-status",
                       headers={"X-PDUFA-Internal-Key": "test-internal-key"})
    assert r.status_code == 200
    assert r.json()["accessMode"] == "single_operator"
    assert r.json()["singleOperatorConfigured"] is True
    assert r.json()["independentVerificationRequiresDistinctReviewers"] is True
    assert "owner@example.org" not in r.text
