"""Version-safe pipeline pagination regression tests."""
from fastapi.testclient import TestClient
from app.main import app, require_storage
from app import source_workspace, program_registry, workspace_delta


def test_page_bounds_and_version(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    app.dependency_overrides[require_storage] = lambda: None
    headers = {"X-PDUFA-Internal-Key": "test-only-secret"}
    snapshot = {"pipeline": [{"id": "PDUFA-000001", "ticker": "ACME", "drug": "Alpha"},
                             {"id": "PDUFA-000002", "ticker": "BETA", "drug": "BetaRx"},
                             {"id": "PDUFA-000003", "ticker": "ACME", "drug": "Gamma"}],
                "asOf": "2026-10-19",
                "sourceHealth": {"streamlitPipelineParity": {"exactPrograms": 3}}}
    version = "a" * 64
    monkeypatch.setattr(source_workspace, "workspace", lambda: snapshot)
    monkeypatch.setattr(program_registry, "number_workspace", lambda value: value)
    monkeypatch.setattr(workspace_delta, "publish", lambda value: {"version": version})
    try:
        with TestClient(app) as client:
            first = client.get("/api/workspace/page?offset=0&limit=2", headers=headers)
            assert first.status_code == 200
            assert first.headers["server-timing"].startswith("workspace_page;dur=")
            assert first.headers["cache-control"] == "private, no-store"
            assert first.json()["total"] == 3
            assert first.json()["version"] == version
            assert len(first.json()["rows"]) == 2
            assert first.json()["nextOffset"] == 2
            last = client.get(f"/api/workspace/page?offset=2&limit=2&version={version}", headers=headers)
            assert last.status_code == 200
            assert [r["id"] for r in last.json()["rows"]] == ["PDUFA-000003"]
            assert last.json()["nextOffset"] is None
            match = client.get("/api/workspace/page?query=PDUFA-000002", headers=headers)
            assert match.status_code == 200
            ticker_match = client.get("/api/workspace/page?query=acme&limit=1", headers=headers)
            assert ticker_match.status_code == 200
            assert ticker_match.json()["total"] == 2
            assert ticker_match.json()["nextOffset"] == 1
            ticker_next = client.get(
                f"/api/workspace/page?query=acme&offset=1&limit=1&version={version}",
                headers=headers,
            )
            assert ticker_next.status_code == 200
            assert ticker_next.json()["rows"][0]["id"] == "PDUFA-000003"
            assert ticker_next.json()["nextOffset"] is None
            drug_match = client.get("/api/workspace/page?query=betarx", headers=headers)
            assert drug_match.json()["total"] == 1
            assert drug_match.json()["rows"][0]["ticker"] == "BETA"
            assert match.json()["total"] == 1
            assert [row["id"] for row in match.json()["rows"]] == ["PDUFA-000002"]
            assert client.get("/api/workspace/page?query=" + "x" * 101,
                              headers=headers).status_code == 422
            assert client.get("/api/workspace/page?limit=101", headers=headers).status_code == 422
            assert client.get("/api/workspace/page?offset=-1", headers=headers).status_code == 422
            assert client.get("/api/workspace/page?version=" + "b" * 64, headers=headers).status_code == 409
    finally:
        app.dependency_overrides.pop(require_storage, None)


def test_page_requires_auth(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    with TestClient(app) as client:
        assert client.get("/api/workspace/page").status_code == 401


def test_page_rejects_unverified_pipeline(monkeypatch):
    """A partial source must never be labeled as a verified candidate page."""
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    app.dependency_overrides[require_storage] = lambda: None
    monkeypatch.setattr(source_workspace, "workspace", lambda: {
        "pipeline": [{"id": "PDUFA-000001"}],
        "sourceHealth": {"streamlitPipelineParity": {"exactPrograms": 2}},
    })
    monkeypatch.setattr(program_registry, "number_workspace", lambda value: value)
    try:
        with TestClient(app) as client:
            response = client.get("/api/workspace/page", headers={
                "X-PDUFA-Internal-Key": "test-only-secret",
            })
            assert response.status_code == 503
            assert response.json()["detail"] == "Verified workspace page unavailable"
    finally:
        app.dependency_overrides.pop(require_storage, None)
