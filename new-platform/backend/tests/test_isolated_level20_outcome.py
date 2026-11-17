from assessment_levels_07_20.level20_outcome import validate_level20_outcome


def example():
    return {
        "nct_id": "NCT04576949", "application_id": "BLA123456",
        "review_cycle_id": "cycle-1", "indication": "Example indication",
        "prediction_version_id": "prediction-1",
        "prediction_frozen_at": "2026-01-01T00:00:00Z",
        "goal_date": "2026-01-05", "official_action_date": "2026-01-07",
        "official_action": "APPROVAL",
        "official_source_url": "https://www.fda.gov/example",
        "source_published_on": "2026-01-07",
        "source_retrieved_on": "2026-01-08",
        "exact_application_cycle_link_documented": True,
        "prediction_record_immutable_verified": True,
        "outcome_exposed_at_prediction": False,
    }


def test_valid_inventory_reports_timing_not_prediction():
    result = validate_level20_outcome(example())
    assert result["eligible_for_owner_review"]
    assert result["action_minus_goal_days"] == 2
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_post_action_prediction_is_ineligible():
    record = example()
    record["prediction_frozen_at"] = "2026-01-08T00:00:00Z"
    assert "PREDICTION_NOT_PRE_ACTION" in validate_level20_outcome(record)["errors"]


def test_exposed_outcome_is_ineligible():
    record = example()
    record["outcome_exposed_at_prediction"] = True
    assert "PREDICTION_OUTCOME_EXPOSURE_NOT_EXCLUDED" in validate_level20_outcome(record)["errors"]


def test_no_exact_cycle_linkage():
    record = example()
    record["exact_application_cycle_link_documented"] = False
    assert "EXACT_APPLICATION_CYCLE_LINK_UNDOCUMENTED" in validate_level20_outcome(record)["errors"]


def test_missing_official_action_source():
    record = example()
    record["official_source_url"] = ""
    assert not validate_level20_outcome(record)["eligible_for_owner_review"]


def test_goal_date_and_action_date_are_distinct():
    record = example()
    record["official_action_date"] = "2026-01-04"
    record["source_published_on"] = "2026-01-04"
    result = validate_level20_outcome(record)
    assert result["eligible_for_owner_review"]
    assert result["action_minus_goal_days"] == -1
