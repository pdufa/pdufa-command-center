from assessment_levels_07_20.level17_disclosures import validate_level17_disclosures


def example():
    return {
        "nct_id": "NCT04576949", "cutoff_on": "2026-01-03",
        "disclosures": [
            {"nct_id": "NCT04576949", "version_id": "v1",
             "source_url": "https://example.org/first", "claim": "Example claim",
             "published_on": "2026-01-01", "retrieved_on": "2026-01-02"},
            {"nct_id": "NCT04576949", "version_id": "v2",
             "source_url": "https://example.org/second", "claim": "Revised claim",
             "published_on": "2026-01-02", "retrieved_on": "2026-01-03"},
        ],
        "contradictions": [
            {"first_version": "v1", "second_version": "v2",
             "description": "Example inconsistency awaiting review"},
        ],
    }


def test_documented_versions_never_generate_forecast():
    result = validate_level17_disclosures(example())
    assert result["eligible_for_owner_review"]
    assert result["contradictions_recorded"] == 1
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_duplicate_versions_rejected():
    record = example()
    record["disclosures"][1]["version_id"] = "v1"
    assert "DUPLICATE_VERSION_ID" in validate_level17_disclosures(record)["errors"]


def test_wrong_trial_disclosure_rejected():
    record = example()
    record["disclosures"][0]["nct_id"] = "NCT00000001"
    assert "DISCLOSURE_TRIAL_MISMATCH_0" in validate_level17_disclosures(record)["errors"]


def test_post_cutoff_source_rejected():
    record = example()
    record["disclosures"][0]["retrieved_on"] = "2026-01-04"
    assert "POST_CUTOFF_DISCLOSURE_0" in validate_level17_disclosures(record)["errors"]


def test_unlinked_contradiction_rejected():
    record = example()
    record["contradictions"][0]["first_version"] = "missing"
    assert "UNLINKED_CONTRADICTION_0" in validate_level17_disclosures(record)["errors"]
