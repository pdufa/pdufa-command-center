from assessment_levels_07_20.level14_pathway import validate_level14_pathway


def example():
    return {
        "nct_id": "NCT04576949", "application_id": "BLA123456",
        "indication": "Example indication", "review_cycle_id": "cycle-1",
        "pathway": "FAST_TRACK", "official_source_url": "https://www.fda.gov/example",
        "published_on": "2026-01-01", "retrieved_on": "2026-01-02",
        "cutoff_on": "2026-01-03", "exact_indication_application_link_documented": True,
    }


def test_valid_inventory_still_abstains():
    result = validate_level14_pathway(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_unknown_designation_rejected():
    record = example()
    record["pathway"] = "GUARANTEED_APPROVAL"
    assert "INVALID_PATHWAY" in validate_level14_pathway(record)["errors"]


def test_no_company_only_linkage():
    record = example()
    record["exact_indication_application_link_documented"] = False
    assert "EXACT_LINKAGE_UNDOCUMENTED" in validate_level14_pathway(record)["errors"]


def test_post_cutoff_source_rejected():
    record = example()
    record["retrieved_on"] = "2026-01-04"
    assert "SOURCE_AFTER_CUTOFF_OR_RETRIEVAL" in validate_level14_pathway(record)["errors"]


def test_wrong_nct_rejected():
    record = example()
    record["nct_id"] = "NCT04576949X"
    assert "INVALID_EXACT_NCT" in validate_level14_pathway(record)["errors"]
