"""Source refreshes poll without returning stale scores or changing the DB."""
import copy
import threading

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main, source_workspace, assessment_service, workspace_response


def test_refresh_in_progress_is_pending_without_scores_or_database(monkeypatch):
    cached = {"pipeline": [{"id": "TRIAL|NCT00000001"}], "sourceHealth": {"state": "PARTIAL", "issues": []}}
    original = copy.deepcopy(cached)
    lock = threading.Lock()
    lock.acquire()
    monkeypatch.setattr(source_workspace, "_REFRESH_LOCK", lock)
    monkeypatch.setattr(source_workspace, "_CACHE", {"payload": cached, "as_time": -1000})
    def forbidden(*args, **kwargs):
        raise AssertionError("A pending source refresh must not access the registry or scoring DB")
    monkeypatch.setattr(workspace_response, "prepared", forbidden)
    monkeypatch.setattr(assessment_service, "Session", forbidden)
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "refresh-test-only")
    main.app.dependency_overrides[main.require_storage] = lambda: None
    try:
        source = source_workspace.workspace()
        assert source["sourceHealth"]["state"] == "STALE"
        assert source["sourceHealth"]["refreshInProgress"] is True
        client = TestClient(main.app)
        try:
            response = client.get("/api/candidate-assessments", headers={"X-PDUFA-Internal-Key": "refresh-test-only"})
            assert response.status_code == 200
            assert response.json() == {"modelVersion": assessment_service.MODEL,
                                       "status": "BUILDING", "total": 1,
                                       "reason": "SOURCE_REFRESH_IN_PROGRESS"}
            assert "records" not in response.json() and "version" not in response.json()
            detail = client.get("/api/candidate-assessments/detail", params={"identity": "TRIAL|NCT00000001"},
                                headers={"X-PDUFA-Internal-Key": "refresh-test-only"})
            assert detail.status_code == 409
        finally:
            client.close()
    finally:
        main.app.dependency_overrides.pop(main.require_storage, None)
        lock.release()
    assert cached == original



def test_protected_pool_waits_for_in_flight_refresh_to_finish(monkeypatch):
    """Fresh interactive reads wait; ordinary research reads still fail closed."""
    import time
    lock = threading.Lock()
    lock.acquire()
    previous = {"pipeline": [{"id": "TRIAL|NCT00000001"}],
                "sourceHealth": {"state": "PARTIAL", "issues": []}}
    fresh = {"pipeline": [{"id": "TRIAL|NCT00000001"}, {"id": "TRIAL|NCT00000002"}],
             "sourceHealth": {"state": "PARTIAL", "issues": []}}
    state = {"payload": previous, "as_time": -1000}
    monkeypatch.setattr(source_workspace, "_REFRESH_LOCK", lock)
    monkeypatch.setattr(source_workspace, "_CACHE", state)
    monkeypatch.setattr(source_workspace, "gather",
                        lambda: (_ for _ in ()).throw(AssertionError("Duplicate fetch")))
    def complete_refresh():
        time.sleep(0.035)
        state.update(payload=fresh, as_time=time.monotonic())
        lock.release()
    worker = threading.Thread(target=complete_refresh)
    worker.start()
    try:
        assert source_workspace.workspace(require_fresh=True) is fresh
        assert source_workspace.workspace() is fresh
        assert fresh["sourceHealth"]["state"] == "PARTIAL"
    finally:
        worker.join(timeout=2)
    assert not worker.is_alive()


def test_fast_api_declares_private_freshness_opt_in():
    import inspect
    params = inspect.signature(main.read_workspace).parameters
    assert "require_fresh" in params
    assert params["require_fresh"].default is False

def test_failed_refresh_still_rejects_stale_source(monkeypatch):
    cached = {"pipeline": [{"id": "TRIAL|NCT00000001"}], "sourceHealth": {"state": "PARTIAL", "issues": []}}
    stale = source_workspace._stale_snapshot(cached, "Published-source refresh failed")
    assert stale["sourceHealth"]["refreshInProgress"] is False
    monkeypatch.setattr(source_workspace, "workspace", lambda: stale)
    monkeypatch.setattr(workspace_response, "prepared", lambda value: value)
    with pytest.raises(HTTPException) as error:
        assessment_service.get_index()
    assert error.value.status_code == 503
