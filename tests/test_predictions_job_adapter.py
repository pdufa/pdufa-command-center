from research.predictions_job_adapter import (
    checklist_for_trial, latest_trial_job, start_prediction_job,
)


def test_start_and_reopen_saved_job(tmp_path):
    assert latest_trial_job(tmp_path, "TRIAL-X") is None
    job = start_prediction_job(tmp_path, "TRIAL-X")
    assert job["status"] == "QUEUED"
    assert latest_trial_job(tmp_path, "TRIAL-X")["job_id"] == job["job_id"]
    checklist = checklist_for_trial(tmp_path, "TRIAL-X")
    assert len(checklist) == 10
    assert all(row["status"] == "NOT_STARTED" for row in checklist)
    assert all(row["trial_id"] == "TRIAL-X" for row in checklist)
    assert checklist_for_trial(tmp_path, "OTHER") == []
