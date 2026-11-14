"""Recipient-public-key handoff for the 19 private FDA page images.

Uses ephemeral X25519 ECDH + HKDF-SHA256 to derive a fresh AES-256 key.
The existing, source-manifest-checked AES-GCM archive is encrypted with
that derived key. GitHub only ever needs the independent recipient's PUBLIC
key. The private key never enters GitHub Actions, Drive, logs, or Git.

This is reviewer evidence transfer, not human adjudication or model labeling.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .hop_fda_visual_archive_crypto import (
    MAX_BYTES, decrypt_to_memory, pack,
)

MAGIC = b"FDA_VISUAL_RECIPIENT_X25519_AESGCM_V1\x00"
CONTEXT = b"PDUFA-fda-visual-source-archive-recipient-v1:"
PUBLIC_BYTES = 32
FINGERPRINT_BYTES = 32
SALT_BYTES = 16
PREFIX_BYTES = len(MAGIC) + FINGERPRINT_BYTES + PUBLIC_BYTES + SALT_BYTES
MAX_ENVELOPE_BYTES = MAX_BYTES + PREFIX_BYTES + 128


def _public_raw(private: X25519PrivateKey) -> bytes:
    return private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _derive(shared_secret: bytes, salt: bytes, fingerprint: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=CONTEXT + fingerprint,
    ).derive(shared_secret)


def seal_for_recipient(
    image_dir: Path,
    batch1_manifest: Path,
    batch2_manifest: Path,
    *,
    recipient_public_raw: bytes,
) -> tuple[bytes, dict]:
    """Encrypt exact 19-source-image cohort for an independently owned key."""
    if not isinstance(recipient_public_raw, bytes) or len(recipient_public_raw) != 32:
        raise ValueError("Reviewer PUBLIC X25519 key must be 32 raw bytes")
    recipient = X25519PublicKey.from_public_bytes(recipient_public_raw)
    ephemeral = X25519PrivateKey.generate()
    salt = os.urandom(SALT_BYTES)
    fingerprint = hashlib.sha256(recipient_public_raw).digest()
    aes_key = _derive(ephemeral.exchange(recipient), salt, fingerprint)
    sealed, source_audit = pack(
        image_dir, batch1_manifest, batch2_manifest, key=aes_key,
    )
    output = (
        MAGIC + fingerprint + _public_raw(ephemeral) + salt + sealed
    )
    if len(output) > MAX_ENVELOPE_BYTES:
        raise ValueError("FDA reviewer archive exceeds recipient envelope size limit")
    return output, {
        "status": "FDA_RECIPIENT_PUBKEY_ENCRYPTED_VISUAL_ARCHIVE_NOT_DELIVERED",
        "encrypted_source_png_files": source_audit["encrypted_png_files"],
        "recipient_public_key_sha256": fingerprint.hex(),
        "public_key_recipient_envelope_authenticated": True,
        "recipient_private_key_loaded_in_ci": False,
        "source_png_plaintext_exported": False,
        "external_private_key_custody_verified": False,
        "drive_upload_completed": False,
        "human_visual_reviews_completed": 0,
        "independently_verified_fda_review_cycles": 0,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "readiness": "REVIEW_REQUIRED",
    }


def open_for_recipient(
    encrypted: bytes, *,
    recipient_private: X25519PrivateKey,
) -> dict[str, bytes]:
    """Offline authenticated read; does not write or publish plaintext."""
    if (
        not isinstance(recipient_private, X25519PrivateKey)
        or not isinstance(encrypted, bytes)
        or not (PREFIX_BYTES + 48) <= len(encrypted) <= MAX_ENVELOPE_BYTES
        or not encrypted.startswith(MAGIC)
    ):
        raise ValueError("Invalid or oversized recipient-encrypted FDA review archive")
    start = len(MAGIC)
    fingerprint = encrypted[start:start + FINGERPRINT_BYTES]
    start += FINGERPRINT_BYTES
    ephemeral_bytes = encrypted[start:start + PUBLIC_BYTES]
    start += PUBLIC_BYTES
    salt = encrypted[start:start + SALT_BYTES]
    start += SALT_BYTES
    if hashlib.sha256(_public_raw(recipient_private)).digest() != fingerprint:
        raise ValueError("This encrypted FDA archive belongs to a different reviewer")
    ephemeral = X25519PublicKey.from_public_bytes(ephemeral_bytes)
    aes_key = _derive(
        recipient_private.exchange(ephemeral), salt, fingerprint,
    )
    return decrypt_to_memory(encrypted[start:], key=aes_key)
