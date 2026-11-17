from assessment_levels_07_20.blind_prediction_package import validate_blind_prediction_package


def sample():
    trial = {"nct_id": "NCT12345678", "application_id": "NDA123456",
             "indication": "Example", "frozen_on": "2024-01-01",
             "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
             "snapshot_sha256": "a" * 64}
    manifest = {"trials": [trial]}
    evidence = [{**{k: trial[k] for k in ("nct_id", "application_id", "indication", "cutoff_on")},
                 "evidence": [{"nct_id": trial["nct_id"], "source_url": "https://example.org/study",
                               "sha256": "c" * 64, "published_on": "2024-01-02",
                               "retrieved_on": "2024-01-03"}]}]
    predictions = [{**trial, "level": 7, "predicted_on": "2024-01-05",
                    "prediction_sha256": "b" * 64, "prediction": "ABSTAIN",
                    "scientific_status": "NOT_VERIFIED"}]
    return manifest, evidence, predictions


def test_valid_join_is_not_accuracy_claim():
    result = validate_blind_prediction_package(*sample())
    assert result["ready_for_independent_blind_review"]
    assert result["accuracy_evaluated"] is False
    assert result["scientific_status"] == "NOT_VERIFIED"


def test_manifest_hash_mismatch_fails():
    manifest, evidence, predictions = sample()
    predictions[0]["snapshot_sha256"] = "d" * 64
    result = validate_blind_prediction_package(manifest, evidence, predictions)
    assert "PREDICTION_0_MANIFEST_SNAPSHOT_SHA256_MISMATCH" in result["errors"]


def test_missing_prediction_fails():
    manifest, evidence, _ = sample()
    result = validate_blind_prediction_package(manifest, evidence, [])
    assert "INCOMPLETE_PREDICTION_COVERAGE" in result["errors"]


def test_unmatched_event_fails():
    manifest, evidence, predictions = sample()
    predictions[0]["application_id"] = "NDA999999"
    result = validate_blind_prediction_package(manifest, evidence, predictions)
    assert "PREDICTION_0_UNMATCHED_EVENT" in result["errors"]


def test_invalid_evidence_blocks_package():
    manifest, evidence, predictions = sample()
    evidence[0]["evidence"][0]["retrieved_on"] = "2024-03-01"
    assert not validate_blind_prediction_package(manifest, evidence, predictions)["ready_for_independent_blind_review"]
