from research.predictions_background_worker import run_queued_prediction_jobs
from research.predictions_job_adapter import start_prediction_job


def test_background_worker_disabled(tmp_path):
    job = start_prediction_job(tmp_path, "T1", assessment_names=["Efficacy"])
    result = run_queued_prediction_jobs(tmp_path, lambda _: {})
    assert result["status"] == "DISABLED"


def test_background_worker_processes_queued_once(tmp_path):
    start_prediction_job(tmp_path, "T1", assessment_names=["Efficacy"])
    result = run_queued_prediction_jobs(
        tmp_path,
        lambda trial_id: {
            "Efficacy": {"findings": "Source reviewed", "source_urls": ["https://www.fda.gov/example"]}
        },
        enabled=True,
    )
    assert result["processed"][0]["decision"] == "ABSTAIN"
    assert result["processed"][0]["status"] == "COMPLETED"
    assert run_queued_prediction_jobs(tmp_path, lambda _: {}, enabled=True)["processed"] == []


def test_background_worker_reports_provider_error_without_faking_result(tmp_path):
    start_prediction_job(tmp_path, "T2", assessment_names=["Efficacy"])
    def broken(_):
        raise ValueError("No verified source")
    result = run_queued_prediction_jobs(tmp_path, broken, enabled=True)
    assert len(result["errors"]) == 1
    assert not result["processed"]
