import os
from fastapi.testclient import TestClient
from app.main import app


def test_health():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["production_scans_enabled"] is False


def test_protected_by_default():
    with TestClient(app) as client:
        resp = client.get("/api/checklists/OCGN/GEM")
        assert resp.status_code in (401, 503)


def test_invalid_ticker_requires_valid_data(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    with TestClient(app) as client:
        resp = client.get("/api/checklists/no!ticker/GEM", headers={"X-PDUFA-Internal-Key": "test-only-secret"})
        assert resp.status_code == 422
