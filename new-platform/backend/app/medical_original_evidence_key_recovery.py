"""Offline-only recovery envelope for the isolated original-evidence AES-256 key.

Never persist the 32-byte production key or the independently generated
recovery wrapping key in source control, CI artifacts, logs, an evidence
receipt, or the database storing the encrypted source documents.

The only allowed backup is AES-GCM wrapped under a *distinct* 256-bit recovery
key kept in a separate, access-controlled system. This module performs no IO
and has no web endpoints. A successful test with synthetic keys establishes
only cryptographic roundtrip behavior, NOT actual offsite backups or KMS.
"""
from __future__ import annotations
import base64
import binascii
import hashlib
import json
import os
import re
import secrets

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA = "MAIN_ACACIA_VAULT_OFFLINE_KEY_ENVELOPE_V1"
SCOPE = "ISOLATED_PDUFA_MEDICAL_PUBLIC_ORIGINAL_EVIDENCE"
KEY_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{2,47}\Z")
ENVELOPE_FIELDS = frozenset(("schema","scope","keyLabel","nonceB64",
                             "wrappedKeyB64","publicKeyFingerprintSha256"))
AAD_PREFIX = b"MAIN_ACACIA_VAULT_OFFLINE_KEY_ENVELOPE_V1|"


class KeyRecoveryError(ValueError):
    """Deliberately does not include inputs, key bytes or decrypted material."""


def _key(value: bytes, purpose: str) -> bytes:
    if not isinstance(value, bytes) or len(value) != 32:
        raise KeyRecoveryError(purpose+" requires independently controlled 256-bit key bytes")
    return value


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _decode(value: str, *, expected: int | None = None) -> bytes:
    if not isinstance(value, str) or len(value) > 400:
        raise KeyRecoveryError("Invalid recovery envelope encoding")
    try:
        raw=base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error):
        raise KeyRecoveryError("Invalid recovery envelope encoding") from None
    if expected is not None and len(raw)!=expected:
        raise KeyRecoveryError("Invalid recovery envelope length")
    return raw


def _aad(key_label: str) -> bytes:
    if not isinstance(key_label,str) or not KEY_LABEL.fullmatch(key_label):
        raise KeyRecoveryError("Invalid key-label identifier")
    return AAD_PREFIX+SCOPE.encode("ascii")+b"|"+key_label.encode("ascii")


def wrap_key_for_offline_backup(source_key: bytes, recovery_key: bytes,
                                *, key_label: str) -> dict:
    """Return ciphertext-only backup metadata. NEVER return the wrapping key."""
    source_key=_key(source_key,"Source encryption")
    recovery_key=_key(recovery_key,"Offline recovery")
    if secrets.compare_digest(source_key,recovery_key):
        raise KeyRecoveryError("Source and recovery keys must be independent")
    aad=_aad(key_label)
    nonce=os.urandom(12)
    wrapped=AESGCM(recovery_key).encrypt(nonce,source_key,aad)
    return {
        "schema":SCHEMA,"scope":SCOPE,"keyLabel":key_label,
        "nonceB64":_b64(nonce),"wrappedKeyB64":_b64(wrapped),
        "publicKeyFingerprintSha256":hashlib.sha256(source_key).hexdigest(),
    }


def restore_key_from_offline_backup(envelope: dict, recovery_key: bytes,
                                   *, expected_label: str) -> bytes:
    """Explicit, in-memory restore only. Do not log/serialize the return value."""
    recovery_key=_key(recovery_key,"Offline recovery")
    if not isinstance(envelope,dict) or frozenset(envelope)!=ENVELOPE_FIELDS or (
        envelope.get("schema")!=SCHEMA or envelope.get("scope")!=SCOPE
    ):
        raise KeyRecoveryError("Unsupported recovery envelope")
    if envelope.get("keyLabel")!=expected_label:
        raise KeyRecoveryError("Incorrect recovery key identifier")
    aad=_aad(expected_label)
    nonce=_decode(envelope.get("nonceB64"),expected=12)
    wrapped=_decode(envelope.get("wrappedKeyB64"))
    if len(wrapped)!=48:
        raise KeyRecoveryError("Invalid encrypted key length")
    fingerprint=envelope.get("publicKeyFingerprintSha256")
    if not isinstance(fingerprint,str) or not re.fullmatch(r"[a-f0-9]{64}",fingerprint):
        raise KeyRecoveryError("Invalid key fingerprint")
    try:
        original=AESGCM(recovery_key).decrypt(nonce,wrapped,aad)
    except Exception:
        raise KeyRecoveryError("Recovery envelope authentication failed") from None
    _key(original,"Restored source encryption")
    if not secrets.compare_digest(hashlib.sha256(original).hexdigest(),fingerprint):
        raise KeyRecoveryError("Recovered encryption key fingerprint mismatch")
    return original


def envelope_integrity_digest(envelope: dict) -> str:
    """Nonsecret manifest digest for comparing independently backed-up copies."""
    if not isinstance(envelope,dict) or frozenset(envelope)!=ENVELOPE_FIELDS:
        raise KeyRecoveryError("Invalid recovery envelope")
    return hashlib.sha256(json.dumps(envelope,sort_keys=True,separators=(",",":")).encode()).hexdigest()
