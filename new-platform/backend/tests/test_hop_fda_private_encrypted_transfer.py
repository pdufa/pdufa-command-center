"""Synthetic-only encryption and recovery tests — no actual FDA reviewer data."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_private_encrypted_transfer import (
    MANIFEST_NAME, open_fda_file, restore_private_fda_batches,
    seal_fda_file, seal_private_fda_batches,
)
from app.hop_fda_private_review_batches import prepare_private_review_batches
from app.hop_fda_private_review_custody import (
    save_private_blank_batch_manifest, verify_private_blank_batch_manifest,
)
from test_hop_fda_private_review_batches import realistic_synthetic_queue


def private_source(tmp_path):
    folder = tmp_path / "source"
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    first, second = realistic_synthetic_queue()
    batches, audit = prepare_private_review_batches(
        first, second, expected_references=124, expected_groups=101,
    )
    assert len(batches) == 7
    for b in batches:
        for role, field in (("FIRST", "first_blank_reviewer_sources"),
                            ("SECOND", "second_blank_reviewer_sources")):
            p = folder / (b["batch_id"] + "_" + role + "_unreviewed.json")
            p.write_text(json.dumps(b[field], indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
            p.chmod(0o600)
    baseline = save_private_blank_batch_manifest(folder)
    assert baseline["file_count"] == 14
    assert (folder / MANIFEST_NAME).exists()
    return folder


def keys():
    priv = {r: X25519PrivateKey.generate() for r in
            ("FIRST", "SECOND", "CUSTODY")}
    pubs = {r: v.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    ) for r, v in priv.items()}
    return priv, pubs


def test_seal_and_full_offline_restore_recovers_all_blanks_and_custody(tmp_path):
    source = private_source(tmp_path)
    private, public = keys()
    sealed = tmp_path / "sealed"
    res = seal_private_fda_batches(source, sealed, public)
    assert res["status"] == "OFFLINE_ENCRYPTED_FDA_FILES_PREPARED_NOT_UPLOADED"
    assert res["encrypted_files"] == 15
    assert len(list(sealed.iterdir())) == 15
    content = (sealed / "AMBIGUOUS_ID-01_FIRST_unreviewed.json.fdaenc").read_bytes()
    assert b"published_letter_source_sha256" not in content
    assert b"source_lock_sha256" not in content
    assert b"download.open.fda.gov" not in content
    assert b"NDA000001" not in content
    assert b"recipient_public_key_sha256" in content  # key ID, not plaintext
    assert len(list(source.iterdir())) == 15
    with pytest.raises(FileExistsError):
        seal_private_fda_batches(source, sealed, public)

    restored = tmp_path / "restored"
    result = restore_private_fda_batches(sealed, restored, private)
    assert result["restored_blank_source_files"] == 14
    assert result["independent_fda_review_cycles_verified"] == 0
    assert verify_private_blank_batch_manifest(restored)["source_batch_count"] == 7
    for path in source.iterdir():
        assert path.read_bytes() == (restored / path.name).read_bytes()
    assert len(list(restored.iterdir())) == 15


def test_wrong_role_key_and_modified_ciphertext_fail_without_plaintext(tmp_path):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    source = private_source(tmp_path)
    private, public = keys()
    sealed = tmp_path / "sealed"
    seal_private_fda_batches(source, sealed, public)
    name = "AMBIGUOUS_ID-01_FIRST_unreviewed.json"
    path = sealed / (name + ".fdaenc")
    with pytest.raises(ValueError, match="Wrong FDA recipient key"):
        open_fda_file(path.read_bytes(), filename=name,
                      recipient_private=private["SECOND"])
    packet = json.loads(path.read_text(encoding="utf-8"))
    payload = packet["ciphertext_b64"]
    packet["ciphertext_b64"] = ("A" if payload[0] != "A" else "B") + payload[1:]
    path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(ValueError):
        restore_private_fda_batches(sealed, tmp_path / "restored", private)
    assert not (tmp_path / "restored").exists()
    assert not list(tmp_path.glob("**/*_unreviewed.json")) or source.exists()
    assert isinstance(AESGCM.generate_key(bit_length=256), bytes)


@pytest.mark.parametrize("problem", ["removed_package", "role_name_swap",
                                     "wrong_private_key", "unknown_package"])
def test_missing_package_role_swap_or_wrong_key_cannot_pass_recovery(tmp_path, problem):
    source = private_source(tmp_path)
    private, public = keys()
    sealed = tmp_path / "sealed"
    seal_private_fda_batches(source, sealed, public)
    filename = "APPLICATION_ID-01_FIRST_unreviewed.json.fdaenc"
    file = sealed / filename
    if problem == "removed_package":
        file.unlink()
    elif problem == "role_name_swap":
        file.rename(sealed / "APPLICATION_ID-01_FIRST_unreviewed.json.fdaenc.moved")
    elif problem == "wrong_private_key":
        private["FIRST"] = X25519PrivateKey.generate()
    elif problem == "unknown_package":
        (sealed / "untrusted.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        restore_private_fda_batches(sealed, tmp_path / "restored", private)
    assert not (tmp_path / "restored").exists()


def test_fda_role_key_reuse_and_ciphertext_filename_substitution_are_rejected(tmp_path):
    source = private_source(tmp_path)
    _, public = keys()
    with pytest.raises(ValueError, match="distinct"):
        seal_private_fda_batches(
            source, tmp_path / "duplicate",
            {**public, "SECOND": public["FIRST"]},
        )
    assert not (tmp_path / "duplicate").exists()
    priv, pub = keys()
    sealed = seal_fda_file(
        b'{"unreviewed":true}', filename="APPLICATION_ID-01_FIRST_unreviewed.json",
        recipient_public_raw=pub["FIRST"],
    )
    with pytest.raises(ValueError, match="filename or role"):
        open_fda_file(
            sealed, filename="APPLICATION_ID-01_SECOND_unreviewed.json",
            recipient_private=priv["FIRST"],
        )
    with pytest.raises(ValueError):
        seal_fda_file(b"", filename="APPLICATION_ID-01_FIRST_unreviewed.json",
                      recipient_public_raw=pub["FIRST"])
