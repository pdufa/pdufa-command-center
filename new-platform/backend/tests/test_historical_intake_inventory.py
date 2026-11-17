from assessment_levels_07_20.historical_intake_inventory import summarize_historical_intake


def sample():
    trial = {"nct_id": "NCT12345678", "application_id": "NDA123456",
             "indication": "Example", "cutoff_on": "2024-02-01"}
    base = {key: trial[key] for key in ("nct_id", "application_id", "indication")}
    source = {"source_url": "https://www.fda.gov/example", "sha256": "a" * 64,
              "published_on": "2024-01-01", "retrieved_on": "2024-01-02"}
    return {"trials": [trial]}, [
        {**base, **source, "source_type": "FDA"},
        {**base, **source, "source_url": "https://clinicaltrials.gov/study/NCT12345678",
         "source_type": "CLINICALTRIALS_GOV"},
    ]


def test_inventory_reports_priority_source_coverage_without_accuracy():
    result = summarize_historical_intake(*sample())
    assert result["intake_metadata_complete"]
    assert result["trial_count"] == 1
    assert result["accuracy_evaluated"] is False


def test_missing_registry_source_is_reported():
    manifest, records = sample()
    result = summarize_historical_intake(manifest, records[:1])
    assert result["trial_inventory"][0]["missing_priority_source_types"] == ["CLINICALTRIALS_GOV"]
    assert not result["intake_metadata_complete"]


def test_post_cutoff_source_is_flagged():
    manifest, records = sample()
    records[0]["retrieved_on"] = "2024-03-01"
    result = summarize_historical_intake(manifest, records)
    assert not result["trial_inventory"][0]["intake_metadata_valid"]


def test_unmatched_source_is_flagged():
    manifest, records = sample()
    records[0]["application_id"] = "NDA999999"
    result = summarize_historical_intake(manifest, records)
    assert "SOURCE_0_UNMATCHED_EVENT" in result["errors"]


def test_empty_cohort_not_complete():
    assert not summarize_historical_intake({"trials": []}, [])["intake_metadata_complete"]
