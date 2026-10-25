from fastapi.testclient import TestClient
from app import main


def test_auth_status_requires_internal_key(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-internal-key")
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/reviewer/auth-status")
    assert response.status_code in (401, 403)


def test_auth_status_does_not_leak_client_id(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-internal-key")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_GOOGLE_CLIENT_ID",
                       "sensitive-client-id.apps.googleusercontent.com")
    with TestClient(main.app) as client:
        response = client.get("/api/scientific-assessment/reviewer/auth-status",
                              headers={"X-PDUFA-Internal-Key": "test-internal-key"})
    assert response.status_code == 200
    assert response.json()["googleClientConfigured"] is True
    assert response.json()["reviewerSelfRegistrationAllowed"] is False
    assert response.json()["scientificScoreAutoPromotionAllowed"] is False
    assert "sensitive-client-id" not in response.text
