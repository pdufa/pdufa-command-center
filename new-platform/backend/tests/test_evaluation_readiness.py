import pytest

from assessment_levels_07_20.evaluation_readiness import validate_evaluation_readiness


def sample():
    return {
        "frozen_manifest_sha256": "a" * 64,
        "prediction_artifact_sha256": "b" * 64,
        "outcome_adjudication_sha256": "c" * 64,
        "protocol_version": "v1",
        "predictions_frozen_before_unblinding": True,
        "outcomes_independently_adjudicated": True,
        "evaluation_protocol_preregistered": True,
        "evaluation_approved_by_owner": True,
    }


def test_complete_attestations_only_enable_separate_evaluation():
    result = validate_evaluation_readiness(sample())
    assert result["ready_for_separate_evaluation"]
    assert result["accuracy"] is None
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


@pytest.mark.parametrize("field", [
    "frozen_manifest_sha256", "prediction_artifact_sha256",
    "outcome_adjudication_sha256", "protocol_version",
    "predictions_frozen_before_unblinding",
    "outcomes_independently_adjudicated",
    "evaluation_protocol_preregistered", "evaluation_approved_by_owner",
])
def test_missing_required_attestation_blocks_evaluation(field):
    record = sample()
    record.pop(field)
    result = validate_evaluation_readiness(record)
    assert not result["ready_for_separate_evaluation"]
    assert result["accuracy"] is None


@pytest.mark.parametrize("field", [
    "predictions_frozen_before_unblinding", "outcomes_independently_adjudicated",
    "evaluation_protocol_preregistered", "evaluation_approved_by_owner",
])
def test_false_attestation_blocks_evaluation(field):
    record = sample()
    record[field] = False
    assert not validate_evaluation_readiness(record)["ready_for_separate_evaluation"]


def test_invalid_hash_blocks_evaluation():
    record = sample()
    record["prediction_artifact_sha256"] = "unverified"
    assert "INVALID_PREDICTION_ARTIFACT_SHA256" in validate_evaluation_readiness(record)["errors"]


def test_nonmapping_rejected():
    with pytest.raises(TypeError):
        validate_evaluation_readiness(None)
