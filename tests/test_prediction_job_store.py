import pytest

from research.prediction_job_store import create_job, load_job, update_assessment


def test_job_stays_queued_until_real_updates(tmp_path):
    job = create_job(tmp_path, "TRIAL-1", ["Efficacy", "Safety"])
    assert job["status"] == "QUEUED"
    assert all(row["status"] == "NOT_STARTED" for row in job["assessments"])
    running = update_assessment(tmp_path, job["job_id"], "Efficacy", "RUNNING")
    assert running["status"] == "RUNNING"
    completed = update_assessment(
        tmp_path, job["job_id"], "Efficacy", "COMPLETED",
        details="Evidence reviewed", evidence=["source-id"], uncertainty="Moderate",
    )
    assert completed["status"] == "RUNNING"
    finished = update_assessment(tmp_path, job["job_id"], "Safety", "COMPLETED")
    assert finished["status"] == "COMPLETED"
    assert load_job(tmp_path, job["job_id"]) == finished


def test_missing_evidence_blocks_completion(tmp_path):
    job = create_job(tmp_path, "TRIAL-2", ["CMC"])
    blocked = update_assessment(tmp_path, job["job_id"], "CMC", "MISSING_EVIDENCE")
    assert blocked["status"] == "BLOCKED"


def test_invalid_assessment_rejected(tmp_path):
    job = create_job(tmp_path, "TRIAL-3", ["Endpoints"])
    with pytest.raises(ValueError):
        update_assessment(tmp_path, job["job_id"], "Unknown", "COMPLETED")
    with pytest.raises(ValueError):
        update_assessment(tmp_path, job["job_id"], "Endpoints", "MADE_UP")
