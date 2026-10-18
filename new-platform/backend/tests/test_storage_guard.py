from fastapi.testclient import TestClient
from app import main as backend


def test_hosted_staging_refuses_ephemeral_sqlite(monkeypatch):
    """Render staging never silently persists checklist inputs on ephemeral disk."""
    monkeypatch.setattr(backend, "REQUIRE_POSTGRES", True)
    monkeypatch.setattr(backend, "DATABASE_URL", "sqlite:///./checklists_dev.sqlite3")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "unit-test-secret")
    with TestClient(backend.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "waiting_for_database"
        assert health.json()["storage_ready"] is False
        assert health.json()["production_scans_enabled"] is False
        for method in ("get", "put"):
            request = getattr(client, method)
            kwargs = {"headers": {"X-PDUFA-Internal-Key": "unit-test-secret"}}
            if method == "put":
                kwargs["json"] = {"version": 0, "selections": {}, "notes": ""}
            response = request("/api/checklists/OCGN/GEM", **kwargs)
            assert response.status_code == 503
