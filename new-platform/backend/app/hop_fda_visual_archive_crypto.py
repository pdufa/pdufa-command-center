"""Authenticated encrypted export of validated FDA reviewer images.

The GitHub repository is PUBLIC. Plaintext image ZIPs, source/page maps and
reviewer identity data must never be uploaded. The encryption key belongs
to the reviewer and is never included in the ciphertext artifact or logs.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import zipfile
from pathlib import Path

from .hop_fda_visual_handoff_preflight import audit_private_visual_handoff

MAGIC = b"FDA_REVIEW_AES256_GCM_V1\x00"
AAD = b"original-fda-pdf-page-evidence-not-adjudicated"
MAX_BYTES = 160_000_000


def external_key() -> bytes:
    import re
    raw = os.environ.get("PDUFA_FDA_REVIEW_ARCHIVE_KEY", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", raw):
        raise ValueError("A separately held 256-bit FDA reviewer archive key is required")
    return bytes.fromhex(raw)


def pack(image_dir: Path, batch1: Path, batch2: Path, *, key: bytes) -> tuple[bytes, dict]:
    """Encrypted output; only an aggregate count is safe for public logs."""
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("Invalid FDA reviewer archive encryption key")
    counts = audit_private_visual_handoff(image_dir, (batch1, batch2))
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, "w", compression=zipfile.ZIP_STORED) as z:
        for name, path in (
            ("manifests/batch1.json", batch1), ("manifests/batch2.json", batch2)
        ):
            z.write(path, name)
        for p in sorted(image_dir.iterdir()):
            z.write(p, "pages/" + p.name)
    source = memory.getvalue()
    if len(source) > MAX_BYTES:
        raise ValueError("Private FDA page archive exceeds encryption size limit")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = os.urandom(12)
    encrypted = MAGIC + nonce + AESGCM(key).encrypt(nonce, source, AAD)
    return encrypted, {
        "status": "ENCRYPTED_PRIVATE_FDA_PAGES_NOT_REVIEWED",
        "encrypted_png_files": counts["private_source_png_count"],
        "plaintext_exported": False,
        "human_visual_reviews_completed": 0,
        "independently_verified_original_fda_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "durability_limited_by_artifact_retention": True,
    }


def decrypt_to_memory(ciphertext: bytes, *, key: bytes) -> dict[str, bytes]:
    """Verify AEAD tag before returning ANY decrypted review material."""
    if (not isinstance(key, bytes) or len(key) != 32 or
            not isinstance(ciphertext, bytes) or not ciphertext.startswith(MAGIC) or
            len(ciphertext) > MAX_BYTES + len(MAGIC) + 80):
        raise ValueError("Malformed FDA reviewer encrypted archive or key")
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    offset = len(MAGIC)
    plaintext = AESGCM(key).decrypt(
        ciphertext[offset:offset + 12], ciphertext[offset + 12:], AAD
    )
    if len(plaintext) > MAX_BYTES:
        raise ValueError("Oversized decrypted FDA evidence bundle")
    data = {}
    import re
    with zipfile.ZipFile(io.BytesIO(plaintext)) as z:
        files = z.infolist()
        if len(files) != 21 or any(
            i.filename in data or i.is_dir() or i.file_size > 8_000_000 or
            not (i.filename in {"manifests/batch1.json", "manifests/batch2.json"} or
                 re.fullmatch(r"pages/[a-f0-9]{64}_page_[0-9]{3}[.]png", i.filename))
            for i in files
        ):
            raise ValueError("FDA reviewer bundle filenames failed validation")
        for i in files:
            data[i.filename] = z.read(i)
    expected = {}
    for name in ("manifests/batch1.json", "manifests/batch2.json"):
        if name not in data:
            raise ValueError("FDA reviewer manifest missing")
        rows = json.loads(data[name])
        if not isinstance(rows, list):
            raise ValueError("FDA reviewer page manifest malformed")
        for row in rows:
            img = "pages/" + row["private_rendered_png_name"]
            if (img in expected or row["model_eligible"] is not False or
                row["human_visual_review_completed"] is not False or
                row["original_fda_action_page_verified"] is not False):
                raise ValueError("FDA reviewed outcome claim or duplicate in archive")
            expected[img] = row["rendered_png_sha256"]
    if len(expected) != 19 or set(data) != set(expected) | {
        "manifests/batch1.json", "manifests/batch2.json"
    }:
        raise ValueError("FDA reviewer image count/source inventory changed")
    for filename, digest in expected.items():
        if (not data[filename].startswith(b"\x89PNG\r\n\x1a\n") or
            hashlib.sha256(data[filename]).hexdigest() != digest):
            raise ValueError("FDA reviewer PNG bytes failed manifest SHA256")
    return data
