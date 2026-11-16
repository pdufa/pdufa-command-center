import json

from assessment_levels_07_20.historical_research_worklist import build_historical_research_worklist


def test_research_worklist_is_serializable_and_unverified():
    manifest = {"trials": [{"nct_id": "NCT12345678", "application_id": "NDA123456",
                            "indication": "Example", "cutoff_on": "2024-02-01"}]}
    result = build_historical_research_worklist(manifest, [])
    assert json.loads(json.dumps(result)) == result
    assert result["task_count"] >= 2
    assert result["collection_executed"] is False
    assert result["accuracy_evaluated"] is False
    assert all(task["availability"] == "UNVERIFIED" for task in result["tasks"])


def test_complete_priority_source_metadata_has_no_missing_work():
    manifest = {"trials": [{"nct_id": "NCT12345678", "application_id": "NDA123456",
                            "indication": "Example", "cutoff_on": "2024-02-01"}]}
    base = {"nct_id": "NCT12345678", "application_id": "NDA123456",
            "indication": "Example", "sha256": "a" * 64,
            "published_on": "2024-01-01", "retrieved_on": "2024-01-02"}
    records = [{**base, "source_type": "FDA", "source_url": "https://www.fda.gov/example"},
               {**base, "source_type": "CLINICALTRIALS_GOV",
                "source_url": "https://clinicaltrials.gov/study/NCT12345678"}]
    result = build_historical_research_worklist(manifest, records)
    assert result["task_count"] == 0
    assert result["scientific_status"] == "NOT_VERIFIED"
