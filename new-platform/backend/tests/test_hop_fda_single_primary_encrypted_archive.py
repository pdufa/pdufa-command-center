"""Synthetic-only FDA single-primary encrypted handoff and restore tests."""
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_single_primary_review import prepare_single_primary_batches
from app.hop_fda_single_primary_encrypted_archive import (
    seal_single_primary_fda_archive, restore_single_primary_fda_archive,
)
from test_hop_fda_private_review_batches import realistic_synthetic_queue


def private_source(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    blank = realistic_synthetic_queue()[0]
    batches, summary = prepare_single_primary_batches(blank)
    assert len(batches) == 7 and summary["published_letter_references"] == 124
    for batch in batches:
        file = folder / (batch["batch_id"] + "_PRIMARY_unreviewed.json")
        file.write_text(json.dumps(batch["primary_blank_source_rows"],
                                   indent=2, sort_keys=True) + "\n", encoding="utf8")
        file.chmod(0o600)
    return folder


def role_keys():
    private = {r: X25519PrivateKey.generate() for r in ("PRIMARY", "CUSTODY")}
    public = {r: k.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        for r, k in private.items()}
    return private, public


def test_two_key_archive_recovers_seven_first_only_files_and_no_second(tmp_path):
    source = private_source(tmp_path)
    private, public = role_keys()
    archive = tmp_path / "sealed"
    seal = seal_single_primary_fda_archive(source, archive, public)
    assert seal["primary_encrypted_packets"] == 7
    assert seal["encrypted_custody_manifests"] == 1
    assert seal["second_reviewer_packets"] == 0
    assert len(list(archive.iterdir())) == 8
    assert not any("SECOND" in p.name for p in archive.iterdir())
    for file in archive.iterdir():
        data = file.read_bytes()
        assert b"published_letter_source_sha256" not in data
        assert b"historical_fda_pdf_url" not in data
        assert b"source_lock_sha256" not in data
    with pytest.raises(FileExistsError):
        seal_single_primary_fda_archive(source, archive, public)
    recovered = tmp_path / "recovered"
    result = restore_single_primary_fda_archive(archive, recovered, private)
    assert result["primary_source_files_restored"] == 7
    assert result["second_reviewer_files_restored"] == 0
    assert result["independent_fda_review_cycles_verified"] == 0
    assert result["prediction_probability"] is None
    assert {p.name: p.read_bytes() for p in recovered.iterdir()} == {
        p.name: p.read_bytes() for p in source.iterdir()
    }


@pytest.mark.parametrize("attack", [
    "alter_ciphertext", "wrong_primary_key", "wrong_custody_key",
    "drop_primary", "drop_custody", "inject_untrusted",
    "rename_role",
])
def test_primary_archive_refuses_bad_keys_and_missing_or_tampered_ciphertext(tmp_path, attack):
    source = private_source(tmp_path)
    private, public = role_keys()
    archive = tmp_path / "sealed"
    seal_single_primary_fda_archive(source, archive, public)
    first = archive / "AMBIGUOUS_ID-01_PRIMARY_unreviewed.json.fdaenc"
    custody = archive / "private_single_primary_custody_manifest.json.fdaenc"
    if attack == "alter_ciphertext":
        data = json.loads(first.read_text())
        value = data["ciphertext_b64"]
        data["ciphertext_b64"] = ("A" if value[0] != "A" else "B") + value[1:]
        first.write_text(json.dumps(data))
    elif attack == "wrong_primary_key":
        private["PRIMARY"] = X25519PrivateKey.generate()
    elif attack == "wrong_custody_key":
        private["CUSTODY"] = X25519PrivateKey.generate()
    elif attack == "drop_primary":
        first.unlink()
    elif attack == "drop_custody":
        custody.unlink()
    elif attack == "inject_untrusted":
        (archive / "unknown.json.fdaenc").write_text("{}")
    elif attack == "rename_role":
        first.rename(archive / "AMBIGUOUS_ID-01_SECOND_unreviewed.json.fdaenc")
    with pytest.raises(ValueError):
        restore_single_primary_fda_archive(archive, tmp_path / "recovered", private)
    assert not (tmp_path / "recovered").exists()


def test_reused_key_and_changed_blank_source_records_are_rejected(tmp_path):
    source = private_source(tmp_path)
    _, public = role_keys()
    with pytest.raises(ValueError, match="Two different"):
        seal_single_primary_fda_archive(
            source, tmp_path / "sealed", {**public, "CUSTODY": public["PRIMARY"]})
    assert not (tmp_path / "sealed").exists()
    file = source / "APPLICATION_ID-01_PRIMARY_unreviewed.json"
    rows = json.loads(file.read_text())
    rows[0]["model_eligible"] = True
    file.write_text(json.dumps(rows))
    with pytest.raises(ValueError):
        seal_single_primary_fda_archive(source, tmp_path / "sealed", public)
    assert not (tmp_path / "sealed").exists()


def test_single_primary_file_source_permission_leak_is_rejected(tmp_path):
    source = private_source(tmp_path)
    _, public = role_keys()
    source.chmod(0o755)
    with pytest.raises(ValueError, match="owner-only"):
        seal_single_primary_fda_archive(source, tmp_path / "sealed", public)
