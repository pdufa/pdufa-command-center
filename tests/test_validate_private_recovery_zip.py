"""Synthetic offline tests for private recovery ZIP manifest validation."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_private_recovery_zip import validate

def make_archive(path, *, bad_hash=False, duplicate=False, missing=False):
    files = {
        "existing/PDUFA_partial_recovery.zip": b"partial",
        "databases/pdufa-main.dump": b"main",
        "databases/pdufa-alpaca.dump": b"alpaca",
    }
    entries = [{"path": name, "bytes": len(data), "sha256": ("0" * 64 if bad_hash and name.endswith("main.dump") else hashlib.sha256(data).hexdigest())} for name, data in files.items()]
    if missing:
        entries.pop()
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        if duplicate:
            archive.writestr("databases/pdufa-main.dump", b"duplicate")
        archive.writestr("ASSEMBLY_MANIFEST.json", json.dumps({"contents": entries, "secrets_included": False}))

def test_valid_archive(tmp_path):
    archive = tmp_path / "ok.zip"
    make_archive(archive)
    result = validate(archive)
    assert result["archive_integrity"] == "PASS"
    assert result["database_restore"] == "NOT_TESTED"
    assert result["deployment_restore"] == "NOT_TESTED"

def test_bad_hash_rejected(tmp_path):
    import pytest
    archive = tmp_path / "bad.zip"
    make_archive(archive, bad_hash=True)
    with pytest.raises(ValueError, match="SHA-256"):
        validate(archive)

def test_missing_manifest_entry_rejected(tmp_path):
    import pytest
    archive = tmp_path / "missing.zip"
    make_archive(archive, missing=True)
    with pytest.raises(ValueError, match="manifest"):
        validate(archive)

def test_duplicate_archive_entry_rejected(tmp_path):
    import pytest
    archive = tmp_path / "duplicate.zip"
    make_archive(archive, duplicate=True)
    with pytest.raises(ValueError, match="Duplicate"):
        validate(archive)
