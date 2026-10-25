"""Offline API and persistence tests for isolated scientific batch control."""
import json
import gzip
import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main, scientific_batch_jobs, scientific_batch_import

A = "NCT04280705"
B = "NCT02142738"
AUTH = {"x-pdufa-internal-key": "batch-test-secret"}


@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://isolated.invalid/test")
    monkeypatch.setattr(scientific_batch_import.scientific_import,
                        "DATABASE_URL", "postgresql+psycopg://isolated.invalid/test")
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "batch-test-secret")
    monkeypatch.setenv("RENDER_SERVICE_ID", "srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED", "1")
    # Do not enter application lifespan: this is an offline, disposable database.
    yield TestClient(main.app)
    engine.dispose()


def test_ui_is_public_but_contains_no_key_and_is_not_cacheable(isolated):
    response = isolated.get("/scientific-assessment/batches")
    assert response.status_code == 200
    assert "Batch Imports" in response.text
    assert "batch-test-secret" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_authentication_guards_every_job_api(isolated):
    assert isolated.get("/api/scientific-assessment/batches").status_code == 401
    assert isolated.get("/api/scientific-assessment/batches/" + "a"*32).status_code == 401
    assert isolated.post("/api/scientific-assessment/batches",
                         json={"nct_ids":[A]}).status_code == 401
    assert isolated.get("/api/scientific-assessment/batches",
                        headers={"x-pdufa-internal-key":"wrong"}).status_code == 401
    assert isolated.get("/api/scientific-assessment/batches", headers=AUTH).json() == {"jobs":[]}


def test_production_and_disabled_mode_cannot_submit(isolated, monkeypatch):
    monkeypatch.setenv("RENDER_SERVICE_ID","production-service-id")
    response=isolated.post("/api/scientific-assessment/batches",json={"nct_ids":[A]},headers=AUTH)
    assert response.status_code == 403
    monkeypatch.setenv("RENDER_SERVICE_ID","srv-dbehn9fb9u1s739ok5vg")
    monkeypatch.setenv("PDUFA_SCIENTIFIC_BATCH_WRITE_ENABLED","0")
    response=isolated.post("/api/scientific-assessment/batches",json={"nct_ids":[A]},headers=AUTH)
    assert response.status_code == 403
    assert isolated.get("/api/scientific-assessment/batches",headers=AUTH).json()["jobs"] == []


@pytest.mark.parametrize("ids", [
    [], ["BAD"], [A,A], [A + "other"], [A] * 26, [" NCT04280705"]
])
def test_invalid_batch_does_not_persist(isolated, ids):
    response=isolated.post("/api/scientific-assessment/batches",
                           json={"nct_ids":ids},headers=AUTH)
    assert response.status_code == 422
    assert isolated.get("/api/scientific-assessment/batches",headers=AUTH).json()["jobs"] == []


def test_submit_is_durable_and_exclusive(isolated):
    with patch("app.scientific_batch_jobs.threading.Thread") as thread:
        result=isolated.post("/api/scientific-assessment/batches",
                             json={"nct_ids":[A,B]},headers=AUTH)
    assert result.status_code == 202
    thread.return_value.start.assert_called_once()
    job=result.json()
    assert job["status"]=="queued"
    assert job["processed"]==0 and job["total"]==2
    job_id=job["id"]
    assert isolated.get("/api/scientific-assessment/batches/"+job_id,
                        headers=AUTH).json()["nct_ids"]==[A,B]
    assert len(isolated.get("/api/scientific-assessment/batches",
                            headers=AUTH).json()["jobs"])==1
    conflict=isolated.post("/api/scientific-assessment/batches",
                            json={"nct_ids":[B]},headers=AUTH)
    assert conflict.status_code==409
    assert "unfinished" in conflict.json()["detail"]


def test_progress_saved_per_trial_error_types_only(isolated):
    job=scientific_batch_jobs.submit_job([A,B],start_worker=False)
    def fake_import(nct_id):
        if nct_id==B:
            raise HTTPError("https://registry.example.invalid/secret",429,"limited",{},None)
        return "imported"
    with patch("app.scientific_batch_import.scientific_import.import_one",
               side_effect=fake_import), patch("app.scientific_batch_import.time.sleep"):
        scientific_batch_jobs._worker(job["id"],[A,B])
    detail=isolated.get("/api/scientific-assessment/batches/"+job["id"],
                        headers=AUTH).json()
    assert detail["status"]=="completed_with_errors"
    assert (detail["processed"],detail["imported"],detail["failed"])==(2,1,1)
    assert detail["completed_at"]
    assert detail["events"][1]["http_status"]==429
    assert "registry.example.invalid" not in json.dumps(detail)
    another=scientific_batch_jobs.submit_job([A],start_worker=False)
    assert another["status"]=="queued"


def test_unexpected_worker_failure_is_recorded_and_unlocks(isolated):
    job=scientific_batch_jobs.submit_job([A],start_worker=False)
    with patch("app.scientific_batch_jobs.scientific_batch_import.run_batch",
               side_effect=RuntimeError("sensitive connection string")):
        scientific_batch_jobs._worker(job["id"],[A])
    detail=scientific_batch_jobs.get_job(job["id"])
    assert detail["status"]=="interrupted"
    assert detail["completed_at"]
    assert "sensitive connection string" not in json.dumps(detail)
    assert scientific_batch_jobs.submit_job([B],start_worker=False)["status"]=="queued"


def test_invalid_detail_id_not_reflected(isolated):
    result=isolated.get("/api/scientific-assessment/batches/something-suspicious",headers=AUTH)
    assert result.status_code==404


def test_recovery_status_requires_auth_and_is_read_only(isolated):
    path="/api/scientific-assessment/batches-recovery-status"
    assert isolated.get(path).status_code==401
    initial=isolated.get(path,headers=AUTH).json()
    assert initial["active_job"] is None
    assert initial["potentially_interrupted"] is False
    job=scientific_batch_jobs.submit_job([A],start_worker=False)
    fresh=isolated.get(path,headers=AUTH).json()
    assert fresh["active_job"]["id"]==job["id"]
    assert fresh["potentially_interrupted"] is False
    # Advance only the diagnostic clock: the database row must remain unchanged.
    future=datetime.now(timezone.utc)+timedelta(hours=2)
    with patch("app.scientific_batch_jobs._now",return_value=future):
        stale=isolated.get(path,headers=AUTH).json()
    assert stale["potentially_interrupted"] is True
    assert stale["manual_review_required"] is True
    assert "No automatic retry" in stale["message"]
    unchanged=scientific_batch_jobs.get_job(job["id"])
    assert unchanged["status"]=="queued"
    assert unchanged["processed"]==0
    assert isolated.post("/api/scientific-assessment/batches",
                         json={"nct_ids":[B]},headers=AUTH).status_code==409


def test_authenticated_scientific_archive_is_descriptive_and_scores_withheld(isolated):
    """Real API readback must not upgrade checksum-valid registry data into efficacy."""
    registry = {
        "protocolSection": {
            "identificationModule": {"nctId": A},
            "designModule": {"designInfo": {"allocation": "RANDOMIZED"},
                             "enrollmentInfo": {"count": 1062}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
            "statusModule": {"overallStatus": "COMPLETED"},
        }
    }
    raw = json.dumps(registry, sort_keys=True, separators=(",", ":")).encode()
    with Session(main.ENGINE) as session:
        session.add(main.FullTrialRecord(
            nct_id=A, payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(),
            summary={"nctId": A}, statistics=[],
            fetched_at=datetime.now(timezone.utc),
        ))
        session.commit()
    assert isolated.get("/api/scientific-assessment",
                        params={"exact_id": "TRIAL|" + A}).status_code == 401
    response = isolated.get("/api/scientific-assessment",
                            params={"exact_id": "TRIAL|" + A}, headers=AUTH)
    assert response.status_code == 200
    data = response.json()
    assert data["exactId"] == "TRIAL|" + A
    assert data["registryEvidenceStatus"] == "source_record_loaded"
    assert data["registryEvidence"]["verificationStatus"] == "source_record_only"
    assert data["registryEvidence"]["metadata"]["enrollment"] == 1062
    assert data["assessment"]["overall_score"] is None
    assert data["assessment"]["status"] == "insufficient_evidence"
    assert len(data["assessment"]["domains"]) == 6
    assert all(x["score"] is None for x in data["assessment"]["domains"].values())
    missing = isolated.get("/api/scientific-assessment",
                           params={"exact_id": "TRIAL|" + B}, headers=AUTH).json()
    assert missing["registryEvidenceStatus"] == "record_not_found"
    assert missing["assessment"]["overall_score"] is None
