"""Tests for the isolated scientific investigation readiness contract."""
from app.scientific_investigation_contract import LAYERS, readiness


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
