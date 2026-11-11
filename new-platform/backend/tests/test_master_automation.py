"""Regression tests for checkpoint invariants, Neon-compatible CAS and read-only gates."""
import copy
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.master_automation import (
    ControllerBase, MANAGED, claim, finish, new_state, public, resume, status, utcnow
)
from app.master_automation_api import install_routes

SHA = "a" * 40
EVIDENCE = "e" * 64


def worker():
    return "ci-test-worker-000001"


def completed_pool(state, run_id=123):
    claim(state, "POOL", worker())
    finish(state, "POOL", worker(), "SUCCEEDED", run_id, EVIDENCE)
    return state


def test_fail_from_focus_then_resume_preserves_only_verified_upstream():
    state = completed_pool(new_state("test-20261111", SHA))
    baseline = copy.deepcopy(state["stages"]["POOL"])
    claim(state, "FOCUS", worker())
    finish(state, "FOCUS", worker(), "FAILED", 222, error_code="SOURCE_VERIFICATION_FAILED")
    assert status(state) == "FAILED"
    assert state["stages"]["FOCUS"]["errorCode"] == "SOURCE_VERIFICATION_FAILED"
    with pytest.raises(ValueError):
        claim(state, "FOCUS", worker())
    resume(state, "FOCUS")
    assert state["stages"]["POOL"] == baseline
    assert state["stages"]["FOCUS"]["status"] == "PENDING"
    assert state["generation"] == 2
    claim(state, "FOCUS", worker())
    finish(state, "FOCUS", worker(), "SUCCEEDED", 223, "f" * 64)
    assert state["stages"]["FOCUS"]["attempts"] == 2
    assert status(state) == "MANAGED_STAGES_COMPLETE"
    with pytest.raises(ValueError):
        resume(state, "FOCUS")
    assert state["stages"]["ATSMS"]["status"] == "OBSERVE_ONLY"
    assert state["stages"]["ASSESSMENTS"]["status"] == "NOT_WIRED"
    assert public(state, 12)["fullEndToEndCertified"] is False


def test_pool_failure_blocks_dependent_focus_but_not_independent_jobs():
    state = new_state("test-20261112", SHA)
    with pytest.raises(ValueError):
        claim(state, "FOCUS", worker())
    claim(state, "POOL", worker())
    finish(state, "POOL", worker(), "FAILED", 456, error_code="GITHUB_RUN_FAILED")
    assert state["stages"]["FOCUS"]["status"] == "BLOCKED"
    assert state["stages"]["BACKUPS"]["status"] == "OBSERVE_ONLY"
    resume(state, "POOL")
    assert state["stages"]["FOCUS"]["status"] == "PENDING"
    completed_pool(state)
    claim(state, "FOCUS", worker())
    assert state["stages"]["FOCUS"]["inputDigest"] != state["stages"]["POOL"]["inputDigest"]


def test_invalid_evidence_cannot_be_stamped_success_and_owner_is_enforced():
    state = new_state("test-20261113", SHA)
    claim(state, "POOL", worker())
    for bad in ("", "not-a-digest", None):
        with pytest.raises(ValueError):
            finish(state, "POOL", worker(), "SUCCEEDED", 123, bad)
    with pytest.raises(ValueError):
        finish(state, "POOL", "wrong-worker", "FAILED", 123, error_code="EXTERNAL_FAILURE")
    assert state["stages"]["POOL"]["status"] == "RUNNING"
    state["stages"]["POOL"]["leaseUntil"] = (utcnow() - timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError):
        finish(state, "POOL", worker(), "FAILED", 123, error_code="LEASE_EXPIRED")
    assert state["stages"]["POOL"]["status"] == "RUNNING"


@pytest.fixture
def api(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    ControllerBase.metadata.create_all(engine)
    app = FastAPI()

    def key(x_pdufa_internal_key: str | None = Header(default=None)):
        if x_pdufa_internal_key != "test-key":
            raise HTTPException(401, "Unauthorized")

    install_routes(app, lambda: engine, key, lambda: None, lambda: None)
    client = TestClient(app, headers={"x-pdufa-internal-key": "test-key"})
    monkeypatch.delenv("PDUFA_MASTER_WRITES_ENABLED", raising=False)
    yield client
    client.close()
    engine.dispose()


def test_api_requires_auth_opt_in_and_optimistic_revision(api, monkeypatch):
    assert TestClient(api.app).get("/api/master-automation").status_code == 401
    overview = api.get("/api/master-automation")
    assert overview.status_code == 200
    assert overview.json()["writesEnabled"] is False
    payload = {"runKey": "2026-11-11-explicit", "sourceSha": SHA}
    assert api.post("/api/master-automation/runs", json=payload).status_code == 503
    monkeypatch.setenv("PDUFA_MASTER_WRITES_ENABLED", "1")
    new = api.post("/api/master-automation/runs", json=payload)
    assert new.status_code == 200, new.text
    row = new.json()
    assert row["version"] == 1
    assert row["status"] == "READY"
    assert api.post("/api/master-automation/runs", json=payload).json()["id"] == row["id"]
    assert api.post("/api/master-automation/runs", json={
        "runKey": payload["runKey"], "sourceSha": "b" * 40,
    }).status_code == 409
    run_id = row["id"]
    endpoint = "/api/master-automation/runs/" + run_id
    bad = api.post(endpoint + "/claim", json={"version": 1, "stage": "FOCUS", "worker": worker()})
    assert bad.status_code == 409
    claimed = api.post(endpoint + "/claim", json={"version": 1, "stage": "POOL", "worker": worker()})
    assert claimed.status_code == 200, claimed.text
    assert api.post(endpoint + "/claim", json={
        "version": 1, "stage": "POOL", "worker": worker(),
    }).status_code == 409
    done = api.post(endpoint + "/complete", json={
        "version": 2, "stage": "POOL", "worker": worker(),
        "conclusion": "SUCCEEDED", "workflowRunId": 321,
        "evidenceDigest": EVIDENCE,
    })
    assert done.status_code == 200, done.text
    assert done.json()["version"] == 3
    assert api.post(endpoint + "/resume", json={"version": 3, "stage": "POOL"}).status_code == 409
    assert api.get(endpoint).json()["stages"][0]["status"] == "SUCCEEDED"


def test_no_unwired_or_independent_stage_claimed():
    state = completed_pool(new_state("test-20261114", SHA))
    for target in ("ASSESSMENTS", "PREDICTIONS", "ATSMS", "BACKUPS"):
        with pytest.raises(ValueError):
            claim(state, target, worker())
