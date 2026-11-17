import hashlib

import pytest

from assessment_levels_07_20.frozen_artifacts import verify_frozen_artifacts


def sample():
    payload = b"frozen evidence bytes"
    return [{"artifact_id": "NCT12345678/source-1", "content": payload,
             "sha256": hashlib.sha256(payload).hexdigest()}]


def test_matching_bytes_verified_without_scientific_claims():
    result = verify_frozen_artifacts(sample())
    assert result["integrity_verified"]
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"


def test_hash_mismatch_fails_closed():
    artifacts = sample()
    artifacts[0]["content"] = b"changed evidence bytes"
    result = verify_frozen_artifacts(artifacts)
    assert not result["integrity_verified"]
    assert "ARTIFACT_0_HASH_MISMATCH" in result["errors"]


def test_duplicate_id_fails_closed():
    artifacts = sample()
    result = verify_frozen_artifacts(artifacts * 2)
    assert "ARTIFACT_1_DUPLICATE_ID" in result["errors"]


def test_missing_bytes_fails_closed():
    artifacts = sample()
    artifacts[0]["content"] = "not bytes"
    assert not verify_frozen_artifacts(artifacts)["integrity_verified"]


def test_empty_list_fails_closed():
    assert "MISSING_ARTIFACTS" in verify_frozen_artifacts([])["errors"]


def test_invalid_container_rejected():
    with pytest.raises(TypeError):
        verify_frozen_artifacts(None)
