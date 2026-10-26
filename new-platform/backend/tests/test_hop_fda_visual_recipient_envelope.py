"""Synthetic recipient public-key FDA visual handoff tests — no real keys."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_visual_recipient_envelope import (
    MAGIC, PREFIX_BYTES, open_for_recipient, seal_for_recipient,
)
from scripts.manage_hop_fda_visual_recipient_keys import (
    PRIV, PUB, _read_hex_key, create_local_keys,
)
from test_hop_fda_visual_archive_crypto import sources


def pub_raw(private: X25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw,
    )


def test_public_only_source_locked_roundtrip_and_wrong_recipient_rejection(tmp_path):
    original = sources(tmp_path)
    reviewer = X25519PrivateKey.generate()
    pub = pub_raw(reviewer)
    archive, report = seal_for_recipient(*original, recipient_public_raw=pub)
    assert archive.startswith(MAGIC)
    assert report["encrypted_source_png_files"] == 19
    assert report["recipient_public_key_sha256"] == hashlib.sha256(pub).hexdigest()
    assert report["recipient_private_key_loaded_in_ci"] is False
    assert report["source_png_plaintext_exported"] is False
    assert report["drive_upload_completed"] is False
    assert report["human_visual_reviews_completed"] == 0
    assert report["independently_verified_fda_review_cycles"] == 0
    assert report["model_eligible_records"] == 0
    assert report["prediction_probability"] is None
    opened = open_for_recipient(archive, recipient_private=reviewer)
    assert len(opened) == 21
    assert opened["manifests/batch1.json"] == original[1].read_bytes()
    assert opened["manifests/batch2.json"] == original[2].read_bytes()
    for path in original[0].iterdir():
        assert opened["pages/" + path.name] == path.read_bytes()
    assert b"synthetic-0" not in archive
    with pytest.raises(ValueError, match="different reviewer"):
        open_for_recipient(
            archive, recipient_private=X25519PrivateKey.generate(),
        )


@pytest.mark.parametrize("modification", [
    "truncated", "malformed_magic", "tampered_recipient_fingerprint",
    "tampered_ephemeral_public", "tampered_salt", "tampered_ciphertext",
])
def test_encrypted_recipient_packet_tampering_fails_closed(tmp_path, modification):
    source = sources(tmp_path)
    reviewer = X25519PrivateKey.generate()
    original, _ = seal_for_recipient(
        *source, recipient_public_raw=pub_raw(reviewer),
    )
    tampered = bytearray(original)
    if modification == "truncated":
        tampered = tampered[:PREFIX_BYTES - 1]
    elif modification == "malformed_magic":
        tampered[0] ^= 1
    elif modification == "tampered_recipient_fingerprint":
        tampered[len(MAGIC)] ^= 1
    elif modification == "tampered_ephemeral_public":
        tampered[len(MAGIC) + 32] ^= 1
    elif modification == "tampered_salt":
        tampered[len(MAGIC) + 64] ^= 1
    elif modification == "tampered_ciphertext":
        tampered[-1] ^= 1
    with pytest.raises((ValueError, InvalidTag)):
        open_for_recipient(bytes(tampered), recipient_private=reviewer)


@pytest.mark.parametrize("badkey", [
    b"", b"\x00" * 31, "not-bytes", b"\x01" * 33,
])
def test_only_exact_public_key_size_allowed_for_sealing(tmp_path, badkey):
    with pytest.raises((ValueError, TypeError)):
        seal_for_recipient(*sources(tmp_path), recipient_public_raw=badkey)


def test_offline_owner_only_keypair_generation_and_cli_key_read(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX permission checks required")
    location = tmp_path / "owner_keys"
    result = create_local_keys(location)
    assert result["status"] == (
        "FDA_RECIPIENT_PUBLIC_KEY_READY_PRIVATE_KEY_LOCALLY_HELD"
    )
    assert (location / PUB).exists()
    assert (location / PRIV).exists()
    assert result["public_key_sha256"] == hashlib.sha256(
        _read_hex_key(location / PUB, private=False),
    ).hexdigest()
    assert os.stat(location / PRIV).st_mode & 0o077 == 0
    assert os.stat(location).st_mode & 0o077 == 0
    assert len(_read_hex_key(location / PRIV, private=True)) == 32
    with pytest.raises(FileExistsError):
        create_local_keys(location)
    image_root = tmp_path / "image_data"
    image_root.mkdir()
    image_files = sources(image_root)
    archive, _ = seal_for_recipient(
        *image_files,
        recipient_public_raw=_read_hex_key(location / PUB, private=False),
    )
    owner = X25519PrivateKey.from_private_bytes(
        _read_hex_key(location / PRIV, private=True)
    )
    assert len(open_for_recipient(archive, recipient_private=owner)) == 21


def test_local_key_file_permission_and_public_repo_path_guard(tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX permission checks required")
    location = tmp_path / "keys"
    create_local_keys(location)
    private = location / PRIV
    private.chmod(0o644)
    with pytest.raises(ValueError, match="only by its owner"):
        _read_hex_key(private, private=True)
    private.chmod(0o600)
    from scripts.manage_hop_fda_visual_recipient_keys import REPO
    with pytest.raises(ValueError):
        create_local_keys(REPO / "unsafe-key-dir-in-repo")
