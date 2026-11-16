from assessment_levels_07_20.level19_prospective import validate_level19_prospective


def example():
    return {
        "nct_id": "NCT04576949", "input_snapshot_id": "snapshot-1",
        "input_digest": "digest-example", "model_artifact_id": "model-1",
        "model_version": "v1", "evaluation_cohort_id": "cohort-1",
        "frozen_at": "2026-01-01T00:00:00Z",
        "first_outcome_available_at": "2026-01-02T00:00:00Z",
        "outcome_exposed_at_freeze": False,
        "inputs_immutable_verified": True,
        "model_frozen_before_outcomes": True,
        "out_of_sample_cohort_verified": True,
        "calibration_metrics_verified": True,
    }


def test_eligible_inventory_never_claims_calibration_or_prediction():
    result = validate_level19_prospective(example())
    assert result["eligible_for_calibration_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_post_outcome_freeze_rejected():
    record = example()
    record["frozen_at"] = "2026-01-03T00:00:00Z"
    assert "NOT_PROSPECTIVE_FREEZE" in validate_level19_prospective(record)["errors"]


def test_exposed_outcome_rejected():
    record = example()
    record["outcome_exposed_at_freeze"] = True
    assert "OUTCOME_EXPOSURE_NOT_EXCLUDED" in validate_level19_prospective(record)["errors"]


def test_no_calibration_evidence_rejected():
    record = example()
    record["calibration_metrics_verified"] = False
    assert "CALIBRATION_NOT_VERIFIED" in validate_level19_prospective(record)["errors"]


def test_naive_time_rejected():
    record = example()
    record["frozen_at"] = "2026-01-01T00:00:00"
    assert "INVALID_UTC_CHRONOLOGY" in validate_level19_prospective(record)["errors"]
