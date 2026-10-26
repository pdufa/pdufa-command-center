"""Synthetic FDA encrypted reviewer handoff safety tests; no real FDA images."""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy

import pytest

pytest.importorskip("cryptography")

from app.hop_fda_visual_archive_crypto import (
    MAGIC, decrypt_to_memory, external_key, pack,
)
from app.hop_fda_visual_handoff_preflight import audit_private_visual_handoff


def sources(tmp_path):
    folder = tmp_path / "private_images"
    folder.mkdir(mode=0o700)
    folder.chmod(0o700)
    batches = ([], [])
    for i in range(19):
        pdf_sha = f"{i + 1:064x}"
        name = f"{pdf_sha}_page_{i:03d}.png"
        body = b"\x89PNG\r\n\x1a\n" + f"synthetic-{i}".encode()
        (folder / name).write_bytes(body)
        batches[0 if i < 9 else 1].append({
            "source_full_pdf_sha256": pdf_sha,
            "pdf_page_index_zero_based": i,
            "private_rendered_png_name": name,
            "rendered_png_sha256": hashlib.sha256(body).hexdigest(),
            "source_page_without_extractable_text": True,
            "human_visual_review_completed": False,
            "original_fda_action_page_verified": False,
            "model_eligible": False,
        })
    first, second = tmp_path / "batch1.json", tmp_path / "batch2.json"
    first.write_text(json.dumps(batches[0]), encoding="utf-8")
    second.write_text(json.dumps(batches[1]), encoding="utf-8")
    return folder, first, second


def test_reviewer_archive_ciphertext_roundtrip_and_source_hashes(tmp_path):
    source = sources(tmp_path)
    assert audit_private_visual_handoff(source[0], source[1:])[
        "private_source_png_count"] == 19
    key = b"\x01" * 32
    protected, status = pack(*source, key=key)
    assert protected.startswith(MAGIC)
    assert b"synthetic-0" not in protected
    assert status["encrypted_png_files"] == 19
    assert status["plaintext_exported"] is False
    assert status["model_eligible_records"] == 0
    assert status["human_visual_reviews_completed"] == 0
    plain = decrypt_to_memory(protected, key=key)
    assert len(plain) == 21
    assert sum(k.startswith("pages/") for k in plain) == 19
    assert all(k.startswith(("pages/", "manifests/")) for k in plain)
    assert len(json.loads(plain["manifests/batch1.json"])) == 9
    assert len(json.loads(plain["manifests/batch2.json"])) == 10


@pytest.mark.parametrize("change", [
    "wrong_key", "tampered_tag", "tampered_header", "short_ciphertext",
])
def test_encryption_rejects_wrong_key_and_modified_bytes(tmp_path, change):
    key = b"\x02" * 32
    protected, _ = pack(*sources(tmp_path), key=key)
    if change == "wrong_key":
        key = b"\x03" * 32
    elif change == "tampered_tag":
        protected = protected[:-1] + bytes([protected[-1] ^ 1])
    elif change == "tampered_header":
        protected = b"BAD" + protected[3:]
    elif change == "short_ciphertext":
        protected = protected[:len(MAGIC) + 5]
    with pytest.raises((ValueError, Exception)):
        decrypt_to_memory(protected, key=key)


@pytest.mark.parametrize("change", [
    "missing_png", "injected_png", "tampered_bitmap",
    "false_human_review", "promoted_model_record",
    "altered_source_page", "symlinked_image",
])
def test_invalid_visual_source_never_encrypted(tmp_path, change):
    folder, first, second = sources(tmp_path)
    a = json.loads(first.read_text(encoding="utf-8"))
    if change == "missing_png":
        (folder / a[0]["private_rendered_png_name"]).unlink()
    elif change == "injected_png":
        (folder / "extra.png").write_bytes(b"\x89PNG\r\n\x1a\nx")
    elif change == "tampered_bitmap":
        with (folder / a[0]["private_rendered_png_name"]).open("ab") as out:
            out.write(b"changed")
    elif change == "false_human_review":
        a[0]["human_visual_review_completed"] = True
    elif change == "promoted_model_record":
        a[0]["model_eligible"] = True
    elif change == "altered_source_page":
        a[0]["pdf_page_index_zero_based"] = 500
    elif change == "symlinked_image":
        target = folder / a[0]["private_rendered_png_name"]
        target.unlink()
        target.symlink_to(first)
    first.write_text(json.dumps(a), encoding="utf-8")
    with pytest.raises(ValueError):
        pack(folder, first, second, key=b"\x04" * 32)


def test_external_key_is_missing_or_malformed_unless_configured(monkeypatch):
    monkeypatch.delenv("PDUFA_FDA_REVIEW_ARCHIVE_KEY", raising=False)
    with pytest.raises(ValueError):
        external_key()
    monkeypatch.setenv("PDUFA_FDA_REVIEW_ARCHIVE_KEY", "too-short")
    with pytest.raises(ValueError):
        external_key()
    monkeypatch.setenv("PDUFA_FDA_REVIEW_ARCHIVE_KEY", "ab" * 32)
    assert external_key() == bytes.fromhex("ab" * 32)



def test_ephemeral_real_source_roundtrip_adapter_never_exports_key_or_ciphertext(tmp_path):
    from scripts.verify_hop_fda_visual_archive_roundtrip import (
        verify_ephemeral_roundtrip,
    )
    image_dir, first, second = sources(tmp_path)
    result = verify_ephemeral_roundtrip(image_dir, first, second)
    assert result == {
        "status": "FDA_PRIVATE_VISUAL_ARCHIVE_EPHEMERAL_ROUNDTRIP_VERIFIED",
        "source_png_images_verified": 19,
        "private_original_manifests_verified": 2,
        "encrypted_archive_roundtrip_in_memory": True,
        "authenticated_decryption_recovered_original_bytes": True,
        "wrong_key_rejected": True,
        "ephemeral_encryption_key_saved": False,
        "encrypted_archive_exported": False,
        "plain_source_data_exported": False,
        "durable_reviewer_storage_configured": False,
        "human_visual_reviews_completed": 0,
        "independently_verified_fda_review_cycles": 0,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
    }
    assert not list(tmp_path.glob("*.aesgcm"))


def test_ephemeral_source_roundtrip_fails_closed_on_modified_manifest(tmp_path):
    from scripts.verify_hop_fda_visual_archive_roundtrip import (
        verify_ephemeral_roundtrip,
    )
    image_dir, first, second = sources(tmp_path)
    rows = json.loads(first.read_text(encoding="utf-8"))
    rows[0]["human_visual_review_completed"] = True
    first.write_text(json.dumps(rows), encoding="utf-8")
    with pytest.raises(ValueError):
        verify_ephemeral_roundtrip(image_dir, first, second)
