"""Tests for the isolated scientific investigation readiness contract."""
from app.scientific_investigation_contract import LAYERS, DEPTH_LEVELS, investigation_plan, readiness
from app.scientific_stage_crosswalk import ASSESSMENT_STAGES, stage_crosswalk
from app.scientific_investigation_20 import investigation_20 as source_stages
import pytest


def test_exactly_eight_layers_and_forty_unique_questions():
    keys = [f"{layer}.{field}" for layer, fields in LAYERS.items() for field in fields]
    assert len(LAYERS) == 8
    assert len(keys) == 40
    assert len(set(keys)) == 40


def test_empty_keynote024_remains_unscored():
    result = readiness({})
    assert result["verified_assessments"] == 0
    assert result["coverage_percent"] == 0
    assert not result["ready_for_analysis"]
    assert result["scientific_score"] is None
    assert result["approval_probability"] is None


def test_self_reported_verification_does_not_pass():
    result = readiness({"trial_design.randomization": {
        "review_status": "verified",
        "source_url": "https://clinicaltrials.gov/study/NCT02142738",
    }})
    assert result["verified_assessments"] == 0


def test_independent_verification_counts_without_scoring():
    evidence = {"trial_design.randomization": {
        "review_status": "verified",
        "independent_verification": True,
        "source_url": "https://clinicaltrials.gov/study/NCT02142738",
    }}
    result = readiness(evidence)
    assert result["verified_assessments"] == 1
    assert result["coverage_percent"] == 2.5
    assert result["scientific_score"] is None


def test_all_verified_is_readiness_not_approval_prediction():
    evidence = {
        f"{layer}.{field}": {
            "review_status": "verified",
            "independent_verification": True,
            "source_url": "https://example.org/evidence",
        }
        for layer, fields in LAYERS.items() for field in fields
    }
    result = readiness(evidence)
    assert result["ready_for_analysis"]
    assert result["verified_assessments"] == 40
    assert result["scientific_score"] is None
    assert result["approval_probability"] is None


def test_eight_depth_levels_create_320_unscored_tasks():
    plan = investigation_plan()
    assert len(DEPTH_LEVELS) == 8
    assert plan["assessments"] == 40
    assert plan["requiredTasks"] == 320
    assert len(plan["tasks"]) == 320
    assert len({(task["assessmentId"], task["depthLevel"]) for task in plan["tasks"]}) == 320
    assert plan["completedTasks"] == 0
    assert all(task["status"] == "pending_independent_review" for task in plan["tasks"])
    assert all(task["scientificScore"] is None for task in plan["tasks"])
    assert not plan["readyForScientificConclusion"]
    assert plan["approvalProbability"] is None


def test_api_exposes_320_pending_tasks_for_verified_archived_trial(monkeypatch):
    """Exercise the real API handler with an isolated in-memory archive stub."""
    from types import SimpleNamespace
    from app import main
    from app import scientific_stored_record
    from app import scientific_registry_evidence
    from app import scientific_investigation_20
    from app import scientific_quantitative_results
    from app import scientific_readiness_grades

    class FakeSession:
        def __init__(self, engine):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def get(self, model, nct_id):
            assert nct_id == "NCT02142738"
            return SimpleNamespace(payload_gzip=b"archived", sha256="0" * 64,
                                   fetched_at=None)

    monkeypatch.setattr(main, "storage_ready", lambda: True)
    monkeypatch.setitem(main._DB_STATE, "available", True)
    monkeypatch.setattr(main, "Session", FakeSession)
    monkeypatch.setattr(scientific_stored_record, "verified_record_from_archive",
                        lambda *args: {"verified": True})
    monkeypatch.setattr(scientific_registry_evidence, "extract_trial_evidence",
                        lambda *args: {"status": "source_only"})
    monkeypatch.setattr(scientific_investigation_20, "investigation_20",
                        lambda *args, **kwargs: _minimal_stages())
    monkeypatch.setattr(scientific_quantitative_results, "reported_quantitative_results",
                        lambda *args: {"status": "source_only"})
    monkeypatch.setattr(scientific_readiness_grades, "review_readiness",
                        lambda *args, **kwargs: {"analysisReadiness": {"grade": "C"}})
    # The evidence ledger is optional and must never self-promote candidates.
    result = main.get_scientific_assessment("TRIAL|NCT02142738")
    assert result["registryEvidenceStatus"] == "source_record_loaded"
    forty = result["investigation40"]
    assert forty["nctId"] == "NCT02142738"
    assert len(forty["layers"]) == 8
    assert forty["verification"]["verified_assessments"] == 0
    assert forty["depthReview"]["requiredTasks"] == 320
    assert len(forty["depthReview"]["tasks"]) == 320
    assert forty["depthReview"]["completedTasks"] == 0
    assert forty["stageCrosswalk"]["stageCount"] == 20
    assert forty["stageCrosswalk"]["assessmentCount"] == 40
    assert forty["stageCrosswalk"]["stagesWithLinkedAssessments"] == 20
    assert forty["stageCrosswalk"]["independentlyVerifiedAssessments"] == 0
    assert result["readinessGrades"]["analysisReadiness"]["grade"] == "C"
    assert result["assessment"]["overall_score"] is None


def _minimal_stages():
    return source_stages(
        "NCT02142738",
        {"protocolSection": {"identificationModule": {"nctId": "NCT02142738"}}},
    )


def test_40_scientific_assessments_link_to_all_20_relevant_stages():
    crosswalk = stage_crosswalk(_minimal_stages())
    expected = {f"{layer}.{field}" for layer, fields in LAYERS.items() for field in fields}
    assert set(ASSESSMENT_STAGES) == expected
    assert crosswalk["stageCount"] == 20
    assert crosswalk["assessmentCount"] == 40
    assert crosswalk["stagesWithLinkedAssessments"] == 20
    assert crosswalk["assessmentStageLinks"] >= 40
    assert len(crosswalk["assessments"]) == 40
    assert len(crosswalk["stages"]) == 20
    assert all(stage["linkedAssessments"] > 0 for stage in crosswalk["stages"])
    assert all(item["independentReviewStatus"] == "pending"
               and item["verifiedEvidence"] is False
               and item["scientificScore"] is None
               for item in crosswalk["assessments"])
    assert crosswalk["independentlyVerifiedAssessments"] == 0
    assert crosswalk["readinessConclusion"] == "NOT_READY"
    assert crosswalk["approvalProbability"] is None


def test_stage_crosswalk_fails_closed_for_partial_or_misleading_inputs():
    dossier = _minimal_stages()
    dossier["levels"] = dossier["levels"][:19]
    with pytest.raises(ValueError, match="20 investigation"):
        stage_crosswalk(dossier)

    dossier = _minimal_stages()
    dossier["levels"][0]["scientificallyVerified"] = True
    with pytest.raises(ValueError, match="cannot be treated"):
        stage_crosswalk(dossier)

    dossier = _minimal_stages()
    dossier["levels"][0]["level"] = 99
    with pytest.raises(ValueError, match="out of order"):
        stage_crosswalk(dossier)
