"""HTTP contract checks for the isolated HOP research endpoint.

Run against the FastAPI app with TestClient; no external DB is required.
"""
from fastapi.testclient import TestClient
from app.main import app

def test_hop_readiness_rejects_missing_credentials(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "unit-test-secret")
    with TestClient(app) as client:
        response = client.get("/api/hop/readiness")
    assert response.status_code == 401

def test_hop_readiness_rejects_wrong_credentials(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "unit-test-secret")
    with TestClient(app) as client:
        response = client.get("/api/hop/readiness", headers={"x-pdufa-internal-key":"wrong"})
    assert response.status_code == 401

def test_hop_readiness_auth_and_abstention(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "unit-test-secret")
    monkeypatch.setenv("PDUFA_REQUIRE_POSTGRES", "true")
    with TestClient(app) as client:
        response = client.get("/api/hop/readiness", headers={"x-pdufa-internal-key":"unit-test-secret"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "RESEARCH_ONLY"
    assert payload["historical_model_eligible"] == 0
    assert payload["model_validated"] is False
    assert payload["prediction_probability"] is None
    assert payload["prediction_available"] is False
