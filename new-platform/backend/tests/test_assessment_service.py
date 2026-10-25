from datetime import datetime, timezone
import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app import main, assessment_service as service, source_workspace, workspace_response
from test_candidate_assessments import fixture

@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-key")
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    monkeypatch.setattr(service, "_STATE", {"key": "", "building": False, "index": None, "error": "", "snapshot": None, "reviews": {}, "token": ""})
    row, registry, reviews = fixture()
    snapshot = {"workspaceVersion": "a" * 64, "sourceHealth": {"state": "LIVE"}, "pipeline": [row, {"id": "TRIAL|NCT00000002", "ticker": "SAME", "programId": "PDUFA-000002"}], "members": {"GEM_JR": {"rows": []}, "GEM": {"rows": []}}}
    monkeypatch.setattr(source_workspace, "workspace", lambda: snapshot)
    monkeypatch.setattr(workspace_response, "prepared", lambda value: value)
    monkeypatch.setattr(service, "review_evidence", lambda: ({row["id"]: reviews}, "AVAILABLE"))
    with Session(engine) as session:
        session.add(main.FullTrialRecord(nct_id="NCT00000001", payload_gzip=b"not-read-by-scorer", sha256="a" * 64, summary=registry, statistics=[{"p_value": "<0.01"}], fetched_at=datetime(2026, 10, 20, tzinfo=timezone.utc)))
        session.commit()
    yield engine, snapshot
    engine.dispose()

def count(engine):
    with Session(engine) as session: return session.scalar(select(func.count(main.CandidateAssessmentHistory.id)))

def test_every_program_21_categories_history_and_no_same_ticker_leak(isolated):
    engine, snapshot = isolated
    index = service.get_index(synchronous=True)
    assert index["total"] == 2 and len(index["records"]) == 2
    assert index["registryLinked"] == 1 and index["registryMissing"] == 1
    for record in index["records"]:
        assert all(len(record[i]) == 17 for i in (1, 2, 3))
    assert index["records"][1][1][2] == 0  # no peer-trial evidence copied
    assert count(engine) == 2
    assert service.get_index(synchronous=True) is index
    assert count(engine) == 2
    detail = service.exact_detail(snapshot["pipeline"][0]["id"])
    assert detail["programId"] == "PDUFA-000001"
    assert detail["reportedStatistics"] == [{"p_value": "<0.01"}]
    assert len(detail["history"]) == 1
    assert detail["changes"] == {}
    # A new source snapshot with identical evidence does not duplicate history.
    snapshot["workspaceVersion"] = "b" * 64
    service.get_index(synchronous=True)
    assert count(engine) == 2
    snapshot["pipeline"][0]["trialFilters"]["safety"] = "FLAGGED"
    snapshot["workspaceVersion"] = "c" * 64
    service.get_index(synchronous=True)
    assert count(engine) == 3
    assert len(service.exact_detail(snapshot["pipeline"][0]["id"])["history"]) == 2

def test_index_exact_scope_stale_rejection_and_http_auth(isolated):
    _, snapshot = isolated
    main.app.dependency_overrides[main.require_storage] = lambda: None
    try:
        service.get_index(synchronous=True)
        client = TestClient(main.app)
        assert client.get("/api/candidate-assessments").status_code == 401
        headers = {"x-pdufa-internal-key": "test-key"}
        assert client.get("/api/candidate-assessments", headers=headers).json()["total"] == 2
        assert client.get("/api/candidate-assessments/detail", params={"identity": "SAME"}, headers=headers).status_code == 404
        assert client.get("/api/candidate-assessments/detail", params={"identity": "TRIAL|NCT00000002"}, headers=headers).json()["models"]["PIPELINE"]["score"] is None
        snapshot["sourceHealth"]["state"] = "STALE"
        assert client.get("/api/candidate-assessments", headers=headers).status_code == 503
    finally: main.app.dependency_overrides.pop(main.require_storage, None)

def test_readonly_mode_does_not_write_histories(isolated, monkeypatch):
    engine, _ = isolated
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "1")
    index = service.get_index(synchronous=True)
    assert index["historyStatus"] == "READ_ONLY" and count(engine) == 0


def test_index_reclaims_temporary_memory_without_changing_scores(isolated, monkeypatch):
    engine, _ = isolated
    calls = []
    monkeypatch.setattr(service, "_reclaim_transient_memory", lambda: calls.append("trim"))
    index = service.get_index(synchronous=True)
    assert index["status"] == "COMPLETE"
    assert index["total"] == 2
    assert calls == ["trim"]
    assert count(engine) == 2
    assert service.get_index(synchronous=True) is index
    assert calls == ["trim"]  # Reuses the verified index; no redundant rebuild.


def test_memory_reclamation_is_safe_when_glibc_is_unavailable(monkeypatch):
    import ctypes
    def missing_libc(_):
        raise OSError("libc is unavailable")
    monkeypatch.setattr(ctypes, "CDLL", missing_libc)
    service._reclaim_transient_memory()  # No exception and no data mutations.
