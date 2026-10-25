"""Offline unit tests: no network or database writes."""
import gzip
import hashlib
import json
from unittest.mock import patch

import pytest

from app.scientific_import import fetch_trial, import_one


def test_invalid_identifier_rejected_before_network():
    with pytest.raises(ValueError, match="Exact NCT"):
        fetch_trial("NCT123")


def test_wrong_registry_identity_rejected():
    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit): return json.dumps({
            "protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}
        }).encode()
    with patch("app.scientific_import.urlopen", return_value=FakeResponse()):
        with pytest.raises(ValueError, match="identity mismatch"):
            fetch_trial("NCT00000001")


def test_refuses_ephemeral_database():
    with patch("app.scientific_import.DATABASE_URL", "sqlite:///tmp.db"):
        with pytest.raises(RuntimeError, match="Persistent PostgreSQL"):
            import_one("NCT00000001")


def test_archive_checksum_and_evidence_roundtrip():
    from app.scientific_stored_record import evidence_from_archive
    record = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    evidence = evidence_from_archive("NCT00000001", gzip.compress(canonical), hashlib.sha256(canonical).hexdigest())
    assert evidence["nctId"] == "NCT00000001"
    with pytest.raises(ValueError, match="checksum mismatch"):
        evidence_from_archive("NCT00000001", gzip.compress(canonical), "0" * 64)


def test_registry_http_404_propagates_without_database_write():
    from urllib.error import HTTPError
    error = HTTPError("https://clinicaltrials.gov/api/v2/studies/NCT00000001", 404, "Not Found", {}, None)
    with patch("app.scientific_import.urlopen", side_effect=error):
        with pytest.raises(HTTPError) as caught:
            fetch_trial("NCT00000001")
    assert caught.value.code == 404


def test_registry_response_size_limit():
    class OversizedResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit):
            assert limit == 10_000_001
            return b"x" * limit
    with patch("app.scientific_import.urlopen", return_value=OversizedResponse()):
        with pytest.raises(ValueError, match="size limit"):
            fetch_trial("NCT04280705")


def test_invalid_json_is_not_archived():
    class InvalidResponse:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, limit): return b"not-json"
    with patch("app.scientific_import.urlopen", return_value=InvalidResponse()):
        with pytest.raises(json.JSONDecodeError):
            fetch_trial("NCT04280705")


def test_archive_rejects_invalid_gzip():
    from app.scientific_stored_record import evidence_from_archive
    with pytest.raises(OSError):
        evidence_from_archive("NCT04280705", b"not-gzip", "0" * 64)


def test_archive_rejects_wrong_trial_identity():
    from app.scientific_stored_record import evidence_from_archive
    record = {"protocolSection": {"identificationModule": {"nctId": "NCT04280705"}}}
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    with pytest.raises(ValueError, match="identity mismatch"):
        evidence_from_archive(
            "NCT00000001", gzip.compress(canonical), hashlib.sha256(canonical).hexdigest()
        )
