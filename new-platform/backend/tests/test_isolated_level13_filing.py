from assessment_levels_07_20.level13_filing import validate_level13_filing


def example():
    return {"nct_id": "NCT04576949", "application_id": "BLA123456",
            "indication": "Example indication", "review_cycle_id": "cycle-1",
            "filing_source_url": "https://example.org/filing",
            "published_on": "2026-01-01", "retrieved_on": "2026-01-02",
            "cutoff_on": "2026-01-03", "exact_linkage_documented": True}


def test_complete_inventory_is_not_an_fda_forecast():
    result = validate_level13_filing(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_no_company_only_linkage():
    record = example()
    record["exact_linkage_documented"] = False
    assert "EXACT_APPLICATION_CYCLE_LINKAGE_UNDOCUMENTED" in validate_level13_filing(record)["errors"]


def test_wrong_application_identity():
    record = example()
    record["application_id"] = "ticker-ABC"
    assert "INVALID_APPLICATION_ID" in validate_level13_filing(record)["errors"]


def test_future_source():
    record = example()
    record["retrieved_on"] = "2026-01-04"
    assert "SOURCE_AFTER_CUTOFF_OR_RETRIEVAL" in validate_level13_filing(record)["errors"]


def test_missing_cycle():
    record = example()
    record["review_cycle_id"] = ""
    assert not validate_level13_filing(record)["eligible_for_owner_review"]
