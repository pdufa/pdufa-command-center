from assessment_levels_07_20.level11_unmet_need import validate_level11_context


def example():
    dossier = {
        "nct_id": "NCT04576949", "indication": "Example condition",
        "disease_subtype": "Example subtype", "treatment_setting": "Second line",
        "source_url": "https://example.org/guideline", "published_on": "2026-01-01",
        "retrieved_on": "2026-01-02", "cutoff_on": "2026-01-03",
        "guideline_version": "2026", "comparator": "Standard therapy",
    }
    return {
        "level10_dossier": dossier, "nct_id": dossier["nct_id"],
        "indication": dossier["indication"], "treatment_setting": dossier["treatment_setting"],
        "alternatives": ["Standard therapy"], "burden_source_url": "https://example.org/burden",
        "published_on": "2026-01-01", "retrieved_on": "2026-01-02", "cutoff_on": "2026-01-03",
    }


def test_valid_inventory_never_becomes_scientific_claim():
    result = validate_level11_context(example())
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_missing_level10_blocks():
    r = example()
    del r["level10_dossier"]
    assert "LEVEL10_EVIDENCE_NOT_READY" in validate_level11_context(r)["errors"]


def test_wrong_trial_blocks():
    r = example()
    r["nct_id"] = "NCT00000001"
    assert "LEVEL10_IDENTITY_MISMATCH_NCT_ID" in validate_level11_context(r)["errors"]


def test_future_burden_source_blocks():
    r = example()
    r["retrieved_on"] = "2026-01-04"
    assert "SOURCE_AFTER_CUTOFF_OR_RETRIEVAL" in validate_level11_context(r)["errors"]


def test_missing_alternatives_blocks():
    r = example()
    r["alternatives"] = []
    assert not validate_level11_context(r)["eligible_for_owner_review"]
