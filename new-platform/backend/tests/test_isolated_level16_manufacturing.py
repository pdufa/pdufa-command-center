from assessment_levels_07_20.level16_manufacturing import validate_level16_manufacturing


def example():
    return {
        "nct_id": "NCT04576949", "application_id": "BLA123456",
        "review_cycle_id": "cycle-1", "indication": "Example indication",
        "cutoff_on": "2026-01-03", "exact_application_cycle_link_documented": True,
        "cmc_state": "UNKNOWN_NONPUBLIC", "inspection_state": "UNKNOWN_NONPUBLIC",
    }


def test_unknown_nonpublic_is_not_a_deficiency():
    result = validate_level16_manufacturing(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_unlinked_application_blocks():
    record = example()
    record["exact_application_cycle_link_documented"] = False
    assert "EXACT_APPLICATION_CYCLE_LINK_UNDOCUMENTED" in validate_level16_manufacturing(record)["errors"]


def test_documented_requires_source():
    record = example()
    record["cmc_state"] = "PUBLIC_DOCUMENTED"
    assert "MISSING_CMC_SOURCE" in validate_level16_manufacturing(record)["errors"]


def test_post_cutoff_inspection_evidence_blocks():
    record = example()
    record["inspection_state"] = "PUBLIC_DOCUMENTED"
    record["inspection_source"] = {
        "official_url": "https://www.fda.gov/example",
        "published_on": "2026-01-01", "retrieved_on": "2026-01-04",
    }
    assert "POST_CUTOFF_INSPECTION_SOURCE" in validate_level16_manufacturing(record)["errors"]


def test_nonpublic_state_cannot_carry_fabricated_source():
    record = example()
    record["cmc_source"] = {"official_url": "https://example.org"}
    assert "SOURCE_WITHOUT_DOCUMENTED_CMC_STATE" in validate_level16_manufacturing(record)["errors"]
