from assessment_levels_07_20.level09_benefit_risk import validate_level9_benefit_risk


def example():
    return {
        "nct_id": "NCT04576949", "indication": "example indication",
        "population": "example population", "cutoff_on": "2026-01-05",
        "reviewer_id": "owner-1",
        "dependencies": {
            str(level): {
                "scientific_status": "VERIFIED",
                "nct_id": "NCT04576949", "indication": "example indication",
                "population": "example population",
                "immutable_review_id": f"review-{level}",
                "reviewed_on": "2026-01-04",
            } for level in (3, 4, 5, 7, 8)
        },
        "benefit_harm_interpretation": {
            "benefit_magnitude": "source-grounded example",
            "harm_magnitude": "source-grounded example",
            "clinical_tradeoff": "review required",
            "uncertainty": "uncertainty review required",
            "source_grounded_rationale": "example for contract testing",
        },
    }


def test_ready_input_never_claims_scientific_completion():
    result = validate_level9_benefit_risk(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_missing_level_7_blocks():
    record = example()
    del record["dependencies"]["7"]
    assert "MISSING_LEVEL_7_REVIEW" in validate_level9_benefit_risk(record)["errors"]


def test_unverified_level_8_blocks():
    record = example()
    record["dependencies"]["8"]["scientific_status"] = "NOT_VERIFIED"
    assert "UNVERIFIED_LEVEL_8" in validate_level9_benefit_risk(record)["errors"]


def test_wrong_population_blocks():
    record = example()
    record["dependencies"]["5"]["population"] = "other"
    assert "LEVEL_5_POPULATION_MISMATCH" in validate_level9_benefit_risk(record)["errors"]


def test_post_cutoff_review_blocks():
    record = example()
    record["dependencies"]["3"]["reviewed_on"] = "2026-01-06"
    assert "POST_CUTOFF_LEVEL_3_REVIEW" in validate_level9_benefit_risk(record)["errors"]


def test_arbitrary_weighted_score_forbidden():
    record = example()
    record["arbitrary_weighted_score"] = 99
    assert "ARBITRARY_WEIGHTED_SCORE_FORBIDDEN" in validate_level9_benefit_risk(record)["errors"]
