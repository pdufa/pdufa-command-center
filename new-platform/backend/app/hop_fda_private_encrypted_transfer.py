"""Offline recipient-key encryption for BLANK FDA source handoff files.

X25519 ephemeral ECDH + HKDF-SHA256 + AES-256-GCM, independently per file.
Three separately held role keys: FIRST, SECOND, CUSTODY. Source records, raw
private keys and the plaintext custody manifest must never enter CI artifacts,
Git, or Google Drive. No network transfer or reviewer assignment here.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey, X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from .hop_fda_private_review_custody import (
    FILENAME, MANIFEST_NAME, verify_private_blank_batch_manifest,
)

FORMAT = "PDUFA_PRIVATE_FDA_HANDOFF_X25519_AES256GCM_V1"
ROLE = ("FIRST", "SECOND", "CUSTODY")
MAX_PACKAGE_BYTES = 4_000_000
MAX_RAW_BYTES = 2_000_000
EXPECTED_BATCHES = 7
EXPECTED_FILES = EXPECTED_BATCHES * 2
FIELDS = frozenset((
    "format", "filename", "role", "recipient_public_key_sha256",
    "ephemeral_public_key_b64", "salt_b64", "nonce_b64", "ciphertext_b64",
))
ARCHIVE_FILE = re.compile(
    r"(?:(?:AMBIGUOUS_ID|APPLICATION_ID)-[0-9]{2}_(?:FIRST|SECOND)_unreviewed[.]json|"
    r"private_blank_fda_batch_custody_manifest[.]json)[.]fdaenc\Z"
)


def _b64(blob: bytes) -> str:
    return base64.b64encode(blob).decode("ascii")


def _unb64(value: object, size: int | None = None) -> bytes:
    if not isinstance(value, str) or len(value) > MAX_PACKAGE_BYTES:
        raise ValueError("Invalid FDA archive encoding")
    try:
        data = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error):
        raise ValueError("Invalid FDA archive encoding") from None
    if size is not None and len(data) != size:
        raise ValueError("Invalid FDA archive field length")
    return data


def _role_for(filename: str) -> str:
    if filename == MANIFEST_NAME:
        return "CUSTODY"
    match = FILENAME.fullmatch(filename)
    if not match:
        raise ValueError("Invalid private FDA reviewer file")
    return match.group(3)


def _aad(filename: str, role: str, fingerprint: str) -> bytes:
    return json.dumps({
        "format": FORMAT, "filename": filename, "role": role,
        "recipient_public_key_sha256": fingerprint,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _key(shared: bytes, salt: bytes, aad: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=salt,
        info=b"PDUFA-FDA-review-archive-v1|" + aad,
    ).derive(shared)


def _public_bytes(private_key: X25519PrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def seal_fda_file(raw: bytes, *, filename: str, recipient_public_raw: bytes) -> bytes:
    role = _role_for(filename)
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_RAW_BYTES:
        raise ValueError("FDA source file outside permitted bounds")
    if not isinstance(recipient_public_raw, bytes) or len(recipient_public_raw) != 32:
        raise ValueError("FDA recipient needs an independently verified X25519 public key")
    recipient = X25519PublicKey.from_public_bytes(recipient_public_raw)
    ephemeral = X25519PrivateKey.generate()
    salt, nonce = os.urandom(16), os.urandom(12)
    fingerprint = hashlib.sha256(recipient_public_raw).hexdigest()
    aad = _aad(filename, role, fingerprint)
    ciphertext = AESGCM(_key(ephemeral.exchange(recipient), salt, aad)).encrypt(
        nonce, raw, aad,
    )
    sealed = {
        "format": FORMAT,
        "filename": filename,
        "role": role,
        "recipient_public_key_sha256": fingerprint,
        "ephemeral_public_key_b64": _b64(_public_bytes(ephemeral)),
        "salt_b64": _b64(salt),
        "nonce_b64": _b64(nonce),
        "ciphertext_b64": _b64(ciphertext),
    }
    return (json.dumps(sealed, sort_keys=True, separators=(",", ":")) + "\n").encode()


def open_fda_file(sealed: bytes, *, filename: str,
                  recipient_private: X25519PrivateKey) -> bytes:
    expected_role = _role_for(filename)
    if not isinstance(sealed, bytes) or len(sealed) > MAX_PACKAGE_BYTES:
        raise ValueError("FDA encrypted archive file too large")
    try:
        package = json.loads(sealed)
    except (UnicodeError, ValueError):
        raise ValueError("FDA encrypted archive format invalid") from None
    if (not isinstance(package, dict) or set(package) != FIELDS
            or package["format"] != FORMAT
            or package["filename"] != filename
            or package["role"] != expected_role):
        raise ValueError("FDA sealed reviewer filename or role mismatch")
    fingerprint = hashlib.sha256(_public_bytes(recipient_private)).hexdigest()
    if package["recipient_public_key_sha256"] != fingerprint:
        raise ValueError("Wrong FDA recipient key for this sealed role")
    eph = X25519PublicKey.from_public_bytes(
        _unb64(package["ephemeral_public_key_b64"], 32)
    )
    salt = _unb64(package["salt_b64"], 16)
    nonce = _unb64(package["nonce_b64"], 12)
    ciphertext = _unb64(package["ciphertext_b64"])
    if not 16 < len(ciphertext) <= MAX_RAW_BYTES + 16:
        raise ValueError("Invalid FDA encrypted source length")
    aad = _aad(filename, expected_role, fingerprint)
    try:
        return AESGCM(_key(recipient_private.exchange(eph), salt, aad)).decrypt(
            nonce, ciphertext, aad,
        )
    except (InvalidTag, ValueError):
        raise ValueError("FDA private envelope authentication failed") from None


def _require_roles(keymap: dict) -> None:
    if set(keymap) != set(ROLE):
        raise ValueError("Three independent FDA role encryption keys are required")


def _private_target(directory: Path, forbidden: Path | None = None) -> Path:
    dest = Path(directory)
    if dest.is_symlink() or dest.exists():
        raise FileExistsError("FDA archive destination must be a new directory")
    dest = dest.resolve()
    if (forbidden is not None and
            (dest == forbidden or dest.is_relative_to(forbidden)
             or forbidden.is_relative_to(dest))):
        raise ValueError("FDA archive source/destination cannot overlap")
    if "public_aggregate_only" in dest.parts:
        raise ValueError("Private FDA records must not enter public artifacts")
    return dest


def _put_private(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY
                 | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(raw)


def seal_private_fda_batches(source: Path, dest: Path,
                             public_keys: dict[str, bytes]) -> dict:
    """Prepare encrypted packages only; never upload or distribute credentials."""
    source = Path(source).resolve()
    dest = _private_target(dest, forbidden=source)
    _require_roles(public_keys)
    if (any(not isinstance(key, bytes) or len(key) != 32
            for key in public_keys.values())
            or len(set(public_keys.values())) != 3):
        raise ValueError("FDA A/B/custody public keys must be distinct raw 32-byte keys")
    audit = verify_private_blank_batch_manifest(source)
    if audit["source_batch_count"] != EXPECTED_BATCHES or audit["private_role_files_integrity_checked"] != EXPECTED_FILES:
        raise ValueError("FDA original private batch baseline incomplete")
    original_files = sorted(x for x in source.iterdir() if x.is_file())
    if (len(original_files) != EXPECTED_FILES + 1
            or any(x.is_symlink() for x in original_files)):
        raise ValueError("Private FDA source file set does not match custody inventory")
    dest.mkdir(mode=0o700, parents=True)
    try:
        role_counts = {role: 0 for role in ROLE}
        for f in original_files:
            role = _role_for(f.name)
            _put_private(dest / (f.name + ".fdaenc"),
                         seal_fda_file(f.read_bytes(), filename=f.name,
                                       recipient_public_raw=public_keys[role]))
            role_counts[role] += 1
        if role_counts != {"FIRST": 7, "SECOND": 7, "CUSTODY": 1}:
            raise ValueError("FDA encrypted archive missing one of the recipient files")
    except BaseException:
        shutil.rmtree(dest)
        raise
    return {
        "status": "OFFLINE_ENCRYPTED_FDA_FILES_PREPARED_NOT_UPLOADED",
        "encrypted_files": 15, "encrypted_first_role_files": 7,
        "encrypted_second_role_files": 7, "encrypted_custody_files": 1,
        "independent_fda_review_cycles_verified": 0,
        "model_eligible_records": 0, "prediction_probability": None,
    }


def restore_private_fda_batches(sealed_dir: Path, dest: Path,
                                 private_keys: dict[str, X25519PrivateKey]) -> dict:
    """Offline role-key recovery into a NEW restricted local plaintext directory."""
    sealed_dir = Path(sealed_dir).resolve()
    dest = _private_target(dest, forbidden=sealed_dir)
    _require_roles(private_keys)
    if not all(isinstance(k, X25519PrivateKey) for k in private_keys.values()):
        raise ValueError("Missing one or more private FDA role decryption keys")
    encrypted = sorted(sealed_dir.iterdir())
    if (len(encrypted) != EXPECTED_FILES + 1 or
            any(p.is_symlink() or not p.is_file() or
                not ARCHIVE_FILE.fullmatch(p.name) for p in encrypted)):
        raise ValueError("FDA encrypted source package set incomplete or unsafe")
    dest.mkdir(mode=0o700, parents=True)
    try:
        for path in encrypted:
            name = path.name[:-len(".fdaenc")]
            role = _role_for(name)
            raw = open_fda_file(path.read_bytes(), filename=name,
                                recipient_private=private_keys[role])
            _put_private(dest / name, raw)
        audit = verify_private_blank_batch_manifest(dest)
        if audit["source_batch_count"] != 7 or audit["private_role_files_integrity_checked"] != 14:
            raise ValueError("Decrypted FDA role files do not match custody baseline")
    except BaseException:
        shutil.rmtree(dest)
        raise
    return {
        "status": "OFFLINE_FDA_ENCRYPTED_RESTORE_VERIFIED_LOCALLY_NOT_UPLOADED",
        "restored_blank_source_files": 14,
        "independent_fda_review_cycles_verified": 0,
        "model_eligible_records": 0, "prediction_probability": None,
    }
