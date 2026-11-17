from assessment_levels_07_20.historical_collection_queue import plan_historical_source_collection


def sample():
    manifest = {"trials": [{"nct_id": "NCT12345678", "application_id": "NDA123456",
                            "indication": "Example", "cutoff_on": "2024-02-01"}]}
    source = {"nct_id": "NCT12345678", "application_id": "NDA123456",
              "indication": "Example", "source_type": "FDA",
              "source_url": "https://www.fda.gov/example", "sha256": "a" * 64,
              "published_on": "2024-01-01", "retrieved_on": "2024-01-02"}
    return manifest, [source]


def test_missing_registry_generates_one_task():
    result = plan_historical_source_collection(*sample())
    assert result["missing_source_task_count"] == 1
    assert result["tasks"][0]["source_type"] == "CLINICALTRIALS_GOV"
    assert not result["collection_executed"]


def test_no_sources_generates_two_primary_source_tasks():
    manifest, _ = sample()
    result = plan_historical_source_collection(manifest, [])
    assert {task["source_type"] for task in result["tasks"]} == {
        "FDA", "CLINICALTRIALS_GOV", "EXISTING_SOURCE_METADATA"
    }


def test_invalid_dates_generate_metadata_review_task():
    manifest, sources = sample()
    sources[0]["retrieved_on"] = "2024-03-01"
    result = plan_historical_source_collection(manifest, sources)
    assert any(task["task"] == "REVIEW_SOURCE_PROVENANCE_AND_DATES" for task in result["tasks"])


def test_queue_does_not_claim_scientific_results():
    result = plan_historical_source_collection(*sample())
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["accuracy_evaluated"] is False
    assert all(task["public_availability"] == "UNKNOWN" for task in result["tasks"])
