from assessment_levels_07_20.level12_replication import validate_level12_replication


def example():
    dossier = {
        "nct_id": "NCT04576949", "indication": "Example condition",
        "disease_subtype": "Example subtype", "treatment_setting": "Second line",
        "source_url": "https://example.org/guideline", "published_on": "2026-01-01",
        "retrieved_on": "2026-01-02", "cutoff_on": "2026-01-03",
        "guideline_version": "2026", "comparator": "Standard therapy",
    }
    return {"level10_dossier": dossier, "nct_id": dossier["nct_id"],
            "cutoff_on": "2026-01-03",
            "studies": [
                {"nct_id": "NCT00000001", "cohort_id": "cohort-a",
                 "independent_cohort_confirmed": True,
                 "source_url": "https://example.org/a",
                 "published_on": "2026-01-01", "retrieved_on": "2026-01-02"},
                {"nct_id": "NCT00000002", "cohort_id": "cohort-b",
                 "independent_cohort_confirmed": True,
                 "source_url": "https://example.org/b",
                 "published_on": "2026-01-01", "retrieved_on": "2026-01-02"},
            ]}


def test_complete_inventory_still_abstains():
    result = validate_level12_replication(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["fda_prediction"] == "ABSTAIN"
    assert result["scientific_score"] is None


def test_duplicate_cohort_rejected():
    r = example()
    r["studies"][1]["cohort_id"] = "cohort-a"
    assert "POTENTIALLY_OVERLAPPING_COHORT" in validate_level12_replication(r)["errors"]


def test_future_retrieval_rejected():
    r = example()
    r["studies"][0]["retrieved_on"] = "2026-01-04"
    assert "SOURCE_AFTER_CUTOFF_0" in validate_level12_replication(r)["errors"]


def test_unconfirmed_independence_rejected():
    r = example()
    r["studies"][0]["independent_cohort_confirmed"] = False
    assert "COHORT_INDEPENDENCE_UNCONFIRMED_0" in validate_level12_replication(r)["errors"]
