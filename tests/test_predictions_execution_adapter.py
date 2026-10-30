import pytest

from research.predictions_execution_adapter import execute_prediction, execute_existing_job
from research.predictions_job_adapter import start_prediction_job


def test_execute_sourced_trial_job_end_to_end(tmp_path):
    result = execute_prediction(
        tmp_path, "NCT-EXAMPLE",
        {"Efficacy": {"findings": "Published endpoint", "source_urls": ["https://clinicaltrials.gov/study/NCT-EXAMPLE"]}},
        assessment_names=["Efficacy", "Safety"],
    )
    assert result["job"]["status"] == "BLOCKED"
    assert result["prediction"]["decision"] == "ABSTAIN"
    assert [r["status"] for r in result["job"]["assessments"]] == ["COMPLETED", "MISSING_EVIDENCE"]


def test_execute_existing_job_once(tmp_path):
    job = start_prediction_job(tmp_path, "NCT-EXAMPLE", assessment_names=["Efficacy"])
    result = execute_existing_job(tmp_path, job["job_id"], {})
    assert result["job"]["status"] == "BLOCKED"
    with pytest.raises(ValueError):
        execute_existing_job(tmp_path, job["job_id"], {})
