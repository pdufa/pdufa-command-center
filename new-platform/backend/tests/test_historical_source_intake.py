from assessment_levels_07_20.historical_source_intake import validate_historical_source_intake


def record():
    return {"nct_id": "NCT12345678", "application_id": "NDA123456",
            "indication": "Example", "source_type": "FDA",
            "source_url": "https://www.fda.gov/example",
            "sha256": "a" * 64, "published_on": "2024-01-01",
            "retrieved_on": "2024-01-03"}


def check(records):
    return validate_historical_source_intake(records, "2024-02-01")


def test_valid_primary_source_is_eligible_not_scored():
    result = check([record()])
    assert result["eligible_for_frozen_evidence"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert not result["accuracy_evaluated"]


def test_post_cutoff_retrieval_rejected():
    source = record()
    source["retrieved_on"] = "2024-02-01"
    assert "SOURCE_0_TEMPORAL_LEAKAGE" in check([source])["errors"]


def test_secondary_only_is_not_primary_evidence():
    source = record()
    source["source_type"] = "SECONDARY_DISCOVERY"
    assert not check([source])["eligible_for_frozen_evidence"]


def test_nested_outcome_is_rejected():
    source = record()
    source["metadata"] = {"nested": [{"fda_decision": "approved"}]}
    assert "SOURCE_0_OUTCOME_LEAKAGE" in check([source])["errors"]


def test_duplicate_source_rejected():
    assert "SOURCE_1_DUPLICATE_SOURCE" in check([record(), record()])["errors"]


def test_invalid_url_and_digest_rejected():
    source = record()
    source["source_url"] = "http://example.org"
    source["sha256"] = "abc"
    result = check([source])
    assert "SOURCE_0_INVALID_SOURCE_URL" in result["errors"]
    assert "SOURCE_0_INVALID_SHA256" in result["errors"]


def test_empty_intake_is_not_ready():
    assert "MISSING_SOURCES" in check([])["errors"]
