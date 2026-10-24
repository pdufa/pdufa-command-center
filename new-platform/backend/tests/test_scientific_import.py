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
