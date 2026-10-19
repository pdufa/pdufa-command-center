"""Full, page and incremental readers must agree without rebuilding the universe."""
import copy
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app import main, program_registry, source_workspace, workspace_response


@pytest.fixture
def workspace_client(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-secret")
    main.app.dependency_overrides[main.require_storage] = lambda: None
    source = {
        "mode": "LIVE_READ_ONLY_GITHUB_SOURCE", "asOf": "2026-10-19",
        "pipeline": [{"id": "TRIAL|ONE", "ticker": "ONE"}],
        "members": {"GEM_JR": {"rows": []}, "GEM": {"rows": []}},
        "sourceHealth": {"state": "PARTIAL", "pipelineSourceParity": {"exactPrograms": 1}},
    }
    current, allocations = [source], []
    monkeypatch.setattr(source_workspace, "workspace", lambda: current[0])
    def number(value):
        allocations.append(value)
        return {**value, "pipeline": [{**r, "programId": "PDUFA-000001"}
                                       for r in value["pipeline"]]}
    monkeypatch.setattr(program_registry, "number_workspace", number)
    monkeypatch.setattr(workspace_response, "_CACHE", {
        "source": None, "snapshot": None, "raw": None, "gzip": None,
    })
    monkeypatch.setattr(main, "_PAGE_CACHE", {"source": None, "snapshot": None, "version": None})
    client = TestClient(main.app, headers={"X-PDUFA-Internal-Key": "test-only-secret"})
    yield client, current, allocations
    client.close()
    main.app.dependency_overrides.pop(main.require_storage, None)


def test_concurrent_readers_share_one_numbered_response(workspace_client):
    client, current, allocations = workspace_client
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.get("/api/workspace"), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.content == responses[0].content for r in responses)
    assert len(allocations) == 1
    full = responses[0].json()
    page = client.get("/api/workspace/page").json()
    assert page["version"] == full["workspaceVersion"]
    assert page["rows"] == full["pipeline"]
    delta = client.get("/api/workspace/delta", params={"since": page["version"]}).json()
    assert delta["unchanged"] and not delta["reset"]
    assert len(allocations) == 1
    assert "programId" not in current[0]["pipeline"][0]


def test_source_replacement_invalidates_full_and_page_together(workspace_client):
    client, current, allocations = workspace_client
    original = client.get("/api/workspace").json()
    current[0] = copy.deepcopy(current[0])
    current[0]["pipeline"][0]["drug"] = "Updated evidence"
    updated = client.get("/api/workspace").json()
    assert updated["workspaceVersion"] != original["workspaceVersion"]
    assert updated["pipeline"][0]["drug"] == "Updated evidence"
    assert client.get("/api/workspace/page", params={"version": original["workspaceVersion"]}).status_code == 409
    assert len(allocations) == 2


def test_stale_response_never_receives_a_verified_version(workspace_client):
    client, current, _ = workspace_client
    verified = client.get("/api/workspace").json()
    current[0] = {**current[0], "mode": "STALE_PREVIOUS_FETCH",
                  "sourceHealth": {**current[0]["sourceHealth"], "state": "STALE"}}
    stale = client.get("/api/workspace").json()
    assert "workspaceVersion" not in stale
    assert stale["sourceHealth"]["state"] == "STALE"
    assert stale["pipeline"] == verified["pipeline"]
    assert client.get("/api/workspace/page").status_code == 503
    assert client.get("/api/workspace/delta").status_code == 503


def test_compression_negotiation_preserves_payload_and_private_caching(workspace_client):
    client, _, _ = workspace_client
    gzip_response = client.get("/api/workspace", headers={"Accept-Encoding": "gzip"})
    raw_response = client.get("/api/workspace", headers={"Accept-Encoding": "identity"})
    assert gzip_response.content == raw_response.content
    assert gzip_response.headers["content-encoding"] == "gzip"
    assert raw_response.headers.get("content-encoding") is None
    assert raw_response.headers["cache-control"] == "private, no-store"
    assert raw_response.headers["server-timing"].startswith("workspace;dur=")
    assert client.get("/api/workspace").headers.get("vary") == "Accept-Encoding"
    body, compressed = workspace_response.encoded(workspace_response._CACHE["source"], "gzip;q=0")
    assert not compressed
    assert body == raw_response.content
