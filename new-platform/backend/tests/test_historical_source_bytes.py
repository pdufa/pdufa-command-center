import hashlib

from assessment_levels_07_20.historical_source_bytes import verify_historical_source_bytes


def fixture():
    data = b"historical public source test fixture"
    url = "https://example.org/public-paper"
    return [{"source_url": url, "sha256": hashlib.sha256(data).hexdigest()}], [
        {"source_url": url, "content_bytes": data}]


def test_exact_bytes_are_verified_but_not_blind_eligible():
    result = verify_historical_source_bytes(*fixture())
    assert result["source_bytes_verified"]
    assert result["verified_source_byte_count"] == 1
    assert result["blind_eligible"] is False


def test_tampered_bytes_rejected():
    records, artifacts = fixture()
    artifacts[0]["content_bytes"] += b"!"
    result = verify_historical_source_bytes(records, artifacts)
    assert not result["source_bytes_verified"]
    assert "SOURCE_0_HASH_MISMATCH" in result["errors"]


def test_missing_artifact_rejected():
    records, _ = fixture()
    result = verify_historical_source_bytes(records, [])
    assert "SOURCE_0_MISSING_ARTIFACT" in result["errors"]


def test_unlinked_artifact_rejected():
    records, artifacts = fixture()
    artifacts.append({"source_url": "https://example.org/other", "content_bytes": b"x"})
    assert "UNLINKED_ARTIFACT" in verify_historical_source_bytes(records, artifacts)["errors"]


def test_empty_corpus_not_verified():
    assert not verify_historical_source_bytes([], [])["source_bytes_verified"]
