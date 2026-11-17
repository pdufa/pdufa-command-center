import hashlib

from assessment_levels_07_20.historical_intake_package import validate_historical_intake_package


def sample():
    payload = b"frozen historical source"
    digest = hashlib.sha256(payload).hexdigest()
    trial = {"nct_id": "NCT12345678", "application_id": "NDA123456",
             "indication": "Example", "frozen_on": "2024-01-01",
             "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
             "snapshot_sha256": digest, "snapshot_artifact_id": "snapshot-1"}
    manifest = {"trials": [trial]}
    source = {"nct_id": trial["nct_id"], "application_id": trial["application_id"],
              "indication": trial["indication"], "source_type": "FDA",
              "source_url": "https://www.fda.gov/example", "sha256": "a" * 64,
              "published_on": "2023-12-20", "retrieved_on": "2023-12-21"}
    evidence = [{**{k: trial[k] for k in ("nct_id", "application_id", "indication", "cutoff_on")},
                 "evidence": [{k: source[k] for k in ("nct_id", "source_url", "sha256", "published_on", "retrieved_on")}]}]
    predictions = [{**trial, "level": 7, "predicted_on": "2024-01-05",
                    "prediction_sha256": "b" * 64, "prediction": "ABSTAIN",
                    "scientific_status": "NOT_VERIFIED"}]
    artifacts = [{"artifact_id": "snapshot-1", "sha256": digest, "content": payload}]
    return manifest, evidence, predictions, artifacts, [source]


def test_complete_source_intake_is_only_review_ready():
    result = validate_historical_intake_package(*sample())
    assert result["ready_for_independent_blind_review"]
    assert not result["accuracy_evaluated"]


def test_missing_sources_block_review():
    manifest, evidence, predictions, artifacts, _ = sample()
    result = validate_historical_intake_package(manifest, evidence, predictions, artifacts, [])
    assert "TRIAL_0_MISSING_SOURCE_INTAKE" in result["errors"]


def test_unmatched_sources_block_review():
    manifest, evidence, predictions, artifacts, sources = sample()
    sources[0]["application_id"] = "NDA999999"
    result = validate_historical_intake_package(manifest, evidence, predictions, artifacts, sources)
    assert "SOURCE_0_UNMATCHED_EVENT" in result["errors"]


def test_late_retrieval_blocks_review():
    manifest, evidence, predictions, artifacts, sources = sample()
    sources[0]["retrieved_on"] = "2024-03-01"
    result = validate_historical_intake_package(manifest, evidence, predictions, artifacts, sources)
    assert not result["ready_for_independent_blind_review"]


def test_secondary_source_blocks_review():
    manifest, evidence, predictions, artifacts, sources = sample()
    sources[0]["source_type"] = "SECONDARY_DISCOVERY"
    assert not validate_historical_intake_package(manifest, evidence, predictions, artifacts, sources)["ready_for_independent_blind_review"]


def test_frozen_citation_without_matching_source_is_rejected():
    manifest, evidence, predictions, artifacts, sources = sample()
    evidence[0]["evidence"][0]["sha256"] = "c" * 64
    result = validate_historical_intake_package(manifest, evidence, predictions, artifacts, sources)
    assert "FROZEN_EVIDENCE_MISSING_SOURCE_PROVENANCE" in result["errors"]


def test_intake_source_without_frozen_citation_is_rejected():
    manifest, evidence, predictions, artifacts, sources = sample()
    extra = dict(sources[0])
    extra["source_url"] = "https://www.fda.gov/another"
    sources.append(extra)
    result = validate_historical_intake_package(manifest, evidence, predictions, artifacts, sources)
    assert "SOURCE_INTAKE_NOT_IN_FROZEN_EVIDENCE" in result["errors"]
