from assessment_levels_07_20.historical_preflight import validate_historical_preflight


def sample():
    trial = {
        "nct_id": "NCT12345678", "application_id": "NDA123456",
        "indication": "Example indication", "frozen_on": "2024-01-01",
        "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
        "snapshot_sha256": "a" * 64,
    }
    evidence = {
        "nct_id": trial["nct_id"], "application_id": trial["application_id"],
        "indication": trial["indication"], "cutoff_on": trial["cutoff_on"],
        "evidence": [{"nct_id": trial["nct_id"], "source_url": "https://example.org/study",
                      "sha256": "b" * 64, "published_on": "2024-01-02",
                      "retrieved_on": "2024-01-03"}],
    }
    return {"trials": [trial]}, [evidence]


def test_complete_preflight_abstains():
    manifest, evidence = sample()
    result = validate_historical_preflight(manifest, evidence)
    assert result["eligible_for_blind_review"]
    assert result["fda_prediction"] == "ABSTAIN"
    assert result["scientific_score"] is None


def test_missing_evidence_fails_closed():
    manifest, _ = sample()
    result = validate_historical_preflight(manifest, [])
    assert "INCOMPLETE_EVIDENCE_COVERAGE" in result["errors"]


def test_post_cutoff_source_rejected():
    manifest, evidence = sample()
    evidence[0]["evidence"][0]["retrieved_on"] = "2024-02-01"
    assert not validate_historical_preflight(manifest, evidence)["eligible_for_blind_review"]


def test_wrong_application_rejected():
    manifest, evidence = sample()
    evidence[0]["application_id"] = "NDA999999"
    assert not validate_historical_preflight(manifest, evidence)["eligible_for_blind_review"]


def test_duplicate_evidence_rejected():
    manifest, evidence = sample()
    assert not validate_historical_preflight(manifest, evidence * 2)["eligible_for_blind_review"]


def test_outcome_leakage_rejected():
    manifest, evidence = sample()
    evidence[0]["fda_outcome"] = "approved"
    assert not validate_historical_preflight(manifest, evidence)["eligible_for_blind_review"]


def test_cutoff_mismatch_rejected():
    manifest, evidence = sample()
    evidence[0]["cutoff_on"] = "2024-01-30"
    assert not validate_historical_preflight(manifest, evidence)["eligible_for_blind_review"]
