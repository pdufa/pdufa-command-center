from assessment_levels_07_20.level07_population_review import validate_level7_review

CRITERIA = ("population_definition", "eligibility_applicability", "baseline_balance",
            "subgroup_prespecification", "multiplicity_adjudication",
            "interaction_interpretation", "clinical_generalizability")


def example():
    record = {"nct_id": "NCT04576949", "population": "Example ITT",
              "cutoff_on": "2026-01-05"}
    for criterion in CRITERIA:
        record[criterion] = {
            "status": "REVIEWED", "nct_id": record["nct_id"],
            "source_url": "https://example.org/original",
            "rationale": "Example rationale; no scientific verification claimed",
            "reviewed_on": "2026-01-04",
        }
    return record


def test_complete_inventory_is_not_scientific_validation():
    result = validate_level7_review(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_missing_prespecification_blocks():
    record = example()
    del record["subgroup_prespecification"]
    assert "UNREVIEWED_SUBGROUP_PRESPECIFICATION" in validate_level7_review(record)["errors"]


def test_unreviewed_multiplicity_blocks():
    record = example()
    record["multiplicity_adjudication"]["status"] = "PENDING"
    assert "UNREVIEWED_MULTIPLICITY_ADJUDICATION" in validate_level7_review(record)["errors"]


def test_wrong_trial_review_blocks():
    record = example()
    record["interaction_interpretation"]["nct_id"] = "NCT00000001"
    assert "WRONG_TRIAL_INTERACTION_INTERPRETATION" in validate_level7_review(record)["errors"]


def test_post_cutoff_review_blocks():
    record = example()
    record["clinical_generalizability"]["reviewed_on"] = "2026-01-06"
    assert "POST_CUTOFF_CLINICAL_GENERALIZABILITY" in validate_level7_review(record)["errors"]


def test_source_and_rationale_required():
    record = example()
    record["population_definition"]["source_url"] = ""
    record["baseline_balance"]["rationale"] = ""
    result = validate_level7_review(record)
    assert "MISSING_SOURCE_POPULATION_DEFINITION" in result["errors"]
    assert "MISSING_RATIONALE_BASELINE_BALANCE" in result["errors"]
