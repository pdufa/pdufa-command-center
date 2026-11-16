import hashlib

from assessment_levels_07_20.frozen_blind_package import validate_frozen_blind_package


def sample():
    payload = b"frozen pre-cutoff trial evidence"
    digest = hashlib.sha256(payload).hexdigest()
    trial = {"nct_id": "NCT12345678", "application_id": "NDA123456",
             "indication": "Example", "frozen_on": "2024-01-01",
             "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
             "snapshot_sha256": digest, "snapshot_artifact_id": "snapshot-1"}
    manifest = {"trials": [trial]}
    evidence = [{"nct_id": trial["nct_id"], "application_id": trial["application_id"],
                 "indication": trial["indication"], "cutoff_on": trial["cutoff_on"],
                 "evidence": [{"nct_id": trial["nct_id"], "source_url": "https://example.org/study",
                               "sha256": "a" * 64, "published_on": "2023-12-20",
                               "retrieved_on": "2023-12-21"}]}]
    predictions = [{**trial, "level": 7, "predicted_on": "2024-01-05",
                    "prediction_sha256": "b" * 64, "prediction": "ABSTAIN",
                    "scientific_status": "NOT_VERIFIED"}]
    artifacts = [{"artifact_id": "snapshot-1", "sha256": digest, "content": payload}]
    return manifest, evidence, predictions, artifacts


def test_complete_frozen_package_only_eligible_for_review():
    result = validate_frozen_blind_package(*sample())
    assert result["ready_for_independent_blind_review"]
    assert result["accuracy_evaluated"] is False


def test_modified_snapshot_blocks_package():
    manifest, evidence, predictions, artifacts = sample()
    artifacts[0]["content"] = b"tampered"
    result = validate_frozen_blind_package(manifest, evidence, predictions, artifacts)
    assert not result["ready_for_independent_blind_review"]
    assert "SNAPSHOT_ARTIFACT_0_HASH_MISMATCH" in result["errors"]


def test_missing_snapshot_blocks_package():
    manifest, evidence, predictions, _ = sample()
    assert not validate_frozen_blind_package(manifest, evidence, predictions, [])["ready_for_independent_blind_review"]


def test_mismatched_prediction_blocks_package():
    manifest, evidence, predictions, artifacts = sample()
    predictions[0]["snapshot_sha256"] = "c" * 64
    assert not validate_frozen_blind_package(manifest, evidence, predictions, artifacts)["ready_for_independent_blind_review"]
