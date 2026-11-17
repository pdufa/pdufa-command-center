import hashlib

import pytest

from assessment_levels_07_20.discovery_source_packaging import package_discovery_source_bytes


def test_package_has_true_hash_and_discovery_only_status():
    data = b"source-document-bytes"
    result = package_discovery_source_bytes(
        "https://www.fda.gov/example", data, "2026-11-16T14:20:00-08:00")
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["byte_count"] == len(data)
    assert result["status"] == "DISCOVERY_ONLY"
    assert result["historical_snapshot_verified"] is False
    assert result["blind_eligible"] is False


@pytest.mark.parametrize("timestamp", ["2026-11-16", "not-a-date", ""])
def test_rejects_missing_timezone_or_invalid_timestamp(timestamp):
    with pytest.raises(ValueError):
        package_discovery_source_bytes("https://example.org/file", b"abc", timestamp)


def test_rejects_empty_bytes():
    with pytest.raises(ValueError):
        package_discovery_source_bytes("https://example.org/file", b"", "2026-11-16T22:20:00Z")


def test_rejects_non_https():
    with pytest.raises(ValueError):
        package_discovery_source_bytes("http://example.org/file", b"abc", "2026-11-16T22:20:00Z")
