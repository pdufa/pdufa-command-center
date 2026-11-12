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
            assert response.headers["retry-after"] == "30"
            assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.pop(require_storage, None)


def test_page_reuses_verified_snapshot_and_refreshes_on_source_change(monkeypatch):
    """No repeated identity allocation for a source object; new objects reverify."""
    from app import main
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    app.dependency_overrides[require_storage] = lambda: None
    source = {"pipeline": [{"id": "PDUFA-000001", "ticker": "ONE"}],
              "sourceHealth": {"streamlitPipelineParity": {"exactPrograms": 1}}}
    current = [source]
    calls = []
    monkeypatch.setattr(source_workspace, "workspace", lambda: current[0])
    def number(value):
        calls.append(value)
        return value
    monkeypatch.setattr(program_registry, "number_workspace", number)
    monkeypatch.setattr(workspace_delta, "publish", lambda value: {"version": "a" * 64 if value is source else "b" * 64})
    monkeypatch.setattr(main, "_PAGE_CACHE", {"source": None, "snapshot": None, "version": None})
    headers = {"X-PDUFA-Internal-Key": "test-only-secret"}
    try:
        with TestClient(app) as client:
            first = client.get("/api/workspace/page", headers=headers)
            assert first.status_code == 200
            first_count = len(calls)
            assert first_count >= 1
            second = client.get("/api/workspace/page?offset=1", headers=headers)
            assert second.status_code == 200
            assert len(calls) == first_count
            replacement = {"pipeline": [{"id": "PDUFA-000002", "ticker": "TWO"}],
                           "sourceHealth": {"streamlitPipelineParity": {"exactPrograms": 1}}}
            current[0] = replacement
            refreshed = client.get("/api/workspace/page", headers=headers)
            assert refreshed.status_code == 200
            assert refreshed.json()["version"] == "b" * 64
            assert refreshed.json()["rows"][0]["ticker"] == "TWO"
            assert len(calls) == first_count + 1
            assert client.get("/api/workspace/page?version=" + "a" * 64,
                              headers=headers).status_code == 409
    finally:
        app.dependency_overrides.pop(require_storage, None)
        main._PAGE_CACHE.update(source=None, snapshot=None, version=None)


def test_source_refresh_page_has_redacted_diagnostic_and_no_verified_version(monkeypatch, caplog):
    """Stale refresh data never receives a page version or a successful status."""
    from app import main, workspace_response
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    app.dependency_overrides[require_storage] = lambda: None
    stale = {
        "mode": "STALE_PREVIOUS_FETCH",
        "pipeline": [{"id": "TRIAL|NCT00000001", "ticker": "TEST"}],
        "members": {"GEM_JR": {"rows": []}, "GEM": {"rows": []}},
        "sourceHealth": {
            "state": "STALE", "refreshInProgress": True,
            "streamlitPipelineParity": {"exactPrograms": 1},
        },
    }
    monkeypatch.setattr(source_workspace, "workspace", lambda: stale)
    monkeypatch.setattr(program_registry, "number_workspace", lambda value: value)
    monkeypatch.setattr(workspace_response, "_CACHE", {
        "source": None, "snapshot": None, "raw": None, "gzip": None,
    })
    monkeypatch.setattr(main, "_PAGE_CACHE", {
        "source": None, "snapshot": None, "version": None,
    })
    try:
        with TestClient(app) as client:
            response = client.get("/api/workspace/page", headers={
                "X-PDUFA-Internal-Key": "test-only-secret",
            })
            assert response.status_code == 503
            assert response.json()["detail"] == "Verified workspace page unavailable"
            assert response.headers["retry-after"] == "30"
            assert response.headers["cache-control"] == "no-store"
            assert "workspaceVersion" not in response.text
            assert "NCT00000001" not in response.text
            assert "PDUFA_WORKSPACE_PAGE_UNVERIFIED reason=SOURCE_REFRESH_IN_PROGRESS" in caplog.text
    finally:
        app.dependency_overrides.pop(require_storage, None)
