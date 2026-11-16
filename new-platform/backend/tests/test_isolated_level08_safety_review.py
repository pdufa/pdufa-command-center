from assessment_levels_07_20.level08_safety_review import validate_level8_review

CRITERIA = ("event_ascertainment", "exposure_comparability", "censoring_followup",
            "discontinuation_review", "serious_event_pattern", "clinical_safety_interpretation")


def example():
    record = {
        "nct_id": "NCT04576949", "population": "Example safety population",
        "cutoff_on": "2026-01-05", "exposure_unit": "PERSON_YEARS",
        "treatment": {"nct_id": "NCT04576949", "events": 2, "person_time": 100.0},
        "comparator": {"nct_id": "NCT04576949", "events": 1, "person_time": 80.0},
    }
    for criterion in CRITERIA:
        record[criterion] = {
            "status": "REVIEWED", "nct_id": "NCT04576949",
            "source_url": "https://example.org/original",
            "rationale": "Example rationale", "reviewed_on": "2026-01-04",
        }
    return record


def test_complete_review_still_abstains():
    result = validate_level8_review(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_missing_person_time_rejected():
    record = example()
    del record["treatment"]["person_time"]
    assert "INVALID_TREATMENT_EVENTS_OR_PERSON_TIME" in validate_level8_review(record)["errors"]


def test_boolean_event_count_rejected():
    record = example()
    record["comparator"]["events"] = True
    assert "INVALID_COMPARATOR_EVENTS_OR_PERSON_TIME" in validate_level8_review(record)["errors"]


def test_wrong_trial_rejected():
    record = example()
    record["treatment"]["nct_id"] = "NCT00000001"
    assert "WRONG_TRIAL_TREATMENT" in validate_level8_review(record)["errors"]


def test_unjustified_poisson_model_rejected():
    record = example()
    record["count_model"] = "INDEPENDENT_POISSON_COUNTS"
    assert "UNJUSTIFIED_COUNT_MODEL" in validate_level8_review(record)["errors"]


def test_unreviewed_ascertainment_rejected():
    record = example()
    record["event_ascertainment"]["status"] = "PENDING"
    assert "UNREVIEWED_EVENT_ASCERTAINMENT" in validate_level8_review(record)["errors"]


def test_post_cutoff_clinical_interpretation_rejected():
    record = example()
    record["clinical_safety_interpretation"]["reviewed_on"] = "2026-01-06"
    assert "POST_CUTOFF_CLINICAL_SAFETY_INTERPRETATION" in validate_level8_review(record)["errors"]
