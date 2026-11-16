from assessment_levels_07_20.historical_collection_progress import summarize_historical_collection_progress


def fixture():
    manifest = {"trials": [{"nct_id": "NCT12345678", "application_id": "NDA123456",
                            "indication": "Example", "cutoff_on": "2024-02-01"}]}
    base = {"nct_id": "NCT12345678", "application_id": "NDA123456",
            "indication": "Example", "sha256": "a" * 64,
            "published_on": "2024-01-01", "retrieved_on": "2024-01-02"}
    sources = [{**base, "source_type": "FDA", "source_url": "https://www.fda.gov/example"},
               {**base, "source_type": "CLINICALTRIALS_GOV",
                "source_url": "https://clinicaltrials.gov/study/NCT12345678"}]
    return manifest, sources


def test_complete_metadata_does_not_claim_bytes_verified():
    result = summarize_historical_collection_progress(*fixture())
    assert result["trials_with_priority_source_metadata"] == 1
    assert result["open_collection_tasks"] == 0
    assert result["source_bytes_verified"] is False
    assert result["collection_executed"] is False


def test_missing_source_creates_open_work():
    manifest, sources = fixture()
    result = summarize_historical_collection_progress(manifest, sources[:1])
    assert result["trials_requiring_review"] == 1
    assert result["open_collection_tasks"] >= 1


def test_invalid_source_is_not_counted_as_valid_metadata():
    manifest, sources = fixture()
    sources[0]["retrieved_on"] = "2024-04-01"
    result = summarize_historical_collection_progress(manifest, sources)
    assert result["trials_with_valid_intake_metadata"] == 0
    assert result["scientific_status"] == "NOT_VERIFIED"
