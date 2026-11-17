from assessment_levels_07_20.level15_precedent import validate_level15_precedent


def example():
    return {
        "nct_id": "NCT04576949", "indication": "Example indication",
        "treatment_setting": "Second line", "cutoff_on": "2026-01-03",
        "precedents": [{
            "application_id": "BLA123456", "indication": "Comparable indication",
            "treatment_setting": "Second line",
            "official_source_url": "https://www.fda.gov/example",
            "published_on": "2026-01-01", "retrieved_on": "2026-01-02",
            "comparability_rationale": "Example comparator context",
            "target_trial_outcome_exposed": False,
            "is_target_application": False,
        }],
    }


def test_inventory_never_claims_prediction():
    result = validate_level15_precedent(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_target_outcome_exposure_blocks():
    record = example()
    record["precedents"][0]["target_trial_outcome_exposed"] = True
    assert "OUTCOME_EXPOSURE_NOT_EXCLUDED_0" in validate_level15_precedent(record)["errors"]


def test_target_application_blocks():
    record = example()
    record["precedents"][0]["is_target_application"] = True
    assert "TARGET_APPLICATION_NOT_EXCLUDED_0" in validate_level15_precedent(record)["errors"]


def test_post_cutoff_evidence_blocks():
    record = example()
    record["precedents"][0]["retrieved_on"] = "2026-01-04"
    assert "POST_CUTOFF_SOURCE_0" in validate_level15_precedent(record)["errors"]


def test_missing_comparability_blocks():
    record = example()
    record["precedents"][0]["comparability_rationale"] = ""
    assert "MISSING_COMPARABILITY_RATIONALE_0" in validate_level15_precedent(record)["errors"]
