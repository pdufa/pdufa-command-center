from research.prediction_job_store import create_job
from research.prediction_assessment_runner import run_evidence_checklist, research_decision


def test_sourced_checklist_updates_without_inventing_prediction(tmp_path):
    job = create_job(tmp_path, "TRIAL-1", ["Efficacy", "Safety"])
    updated = run_evidence_checklist(tmp_path, job["job_id"], {
        "Efficacy": {
            "source_urls": ["https://clinicaltrials.gov/study/NCT123"],
            "findings": "Primary endpoint results available",
            "uncertainty": "Review needed",
        }
    })
    assert updated["status"] == "BLOCKED"
    assert [a["status"] for a in updated["assessments"]] == ["COMPLETED", "MISSING_EVIDENCE"]
    assert research_decision(updated)["decision"] == "ABSTAIN"
    assert research_decision(updated)["probabilities"] is None


def test_complete_evidence_still_requires_model_validation(tmp_path):
    job = create_job(tmp_path, "TRIAL-2", ["Efficacy"])
    updated = run_evidence_checklist(tmp_path, job["job_id"], {
        "Efficacy": {
            "source_urls": ["https://www.fda.gov/example"],
            "findings": "Reviewed evidence",
        }
    })
    assert updated["status"] == "COMPLETED"
    result = research_decision(updated)
    assert result["decision"] == "ABSTAIN"
    assert result["readiness"] == "EVIDENCE_RECORDED_MODEL_NOT_VALIDATED"
