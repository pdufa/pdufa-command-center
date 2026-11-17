import hashlib

from assessment_levels_07_20.cohort_snapshot_integrity import verify_cohort_snapshots


def fixture():
    payload = b"frozen historical evidence"
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {"trials": [{
        "nct_id": "NCT12345678", "application_id": "NDA123456",
        "indication": "Example indication", "frozen_on": "2024-01-01",
        "cutoff_on": "2024-02-01", "decision_on": "2024-04-01",
        "snapshot_artifact_id": "snapshot-1", "snapshot_sha256": digest,
    }]}
    artifacts = [{"artifact_id": "snapshot-1", "sha256": digest, "content": payload}]
    return manifest, artifacts


def test_matching_bytes_and_manifest_pass_without_prediction():
    manifest, artifacts = fixture()
    result = verify_cohort_snapshots(manifest, artifacts)
    assert result["snapshots_verified"]
    assert result["fda_prediction"] == "ABSTAIN"


def test_tampered_bytes_fail():
    manifest, artifacts = fixture()
    artifacts[0]["content"] = b"tampered"
    assert not verify_cohort_snapshots(manifest, artifacts)["snapshots_verified"]


def test_manifest_hash_mismatch_fails():
    manifest, artifacts = fixture()
    manifest["trials"][0]["snapshot_sha256"] = "a" * 64
    assert "SNAPSHOT_MANIFEST_HASH_MISMATCH" in verify_cohort_snapshots(manifest, artifacts)["errors"]


def test_missing_artifact_fails():
    manifest, _ = fixture()
    assert not verify_cohort_snapshots(manifest, [])["snapshots_verified"]


def test_extra_artifact_fails():
    manifest, artifacts = fixture()
    artifacts.append({"artifact_id": "extra", "sha256": hashlib.sha256(b"x").hexdigest(), "content": b"x"})
    assert "SNAPSHOT_ARTIFACT_SET_MISMATCH" in verify_cohort_snapshots(manifest, artifacts)["errors"]


def test_missing_artifact_identifier_fails():
    manifest, artifacts = fixture()
    manifest["trials"][0].pop("snapshot_artifact_id")
    assert not verify_cohort_snapshots(manifest, artifacts)["snapshots_verified"]
