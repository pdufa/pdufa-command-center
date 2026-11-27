"""Offline, no-secret-in-CI FDA original-source recipient archive transfer.

Operations are explicit: generate an independently held local reviewer key
(POSIX permissions enforced), encrypt using its PUBLIC key, or locally
decrypt with its PRIVATE key. This script does not call Google Drive or
upload files. Never run generate/open inside public GitHub Actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_visual_recipient_envelope import (
    open_for_recipient, seal_for_recipient,
)

REPO = Path(__file__).resolve().parents[3]
PUB = "fda_visual_review_recipient_public.hex"
PRIV = "fda_visual_review_recipient_private.hex"
SENSITIVE_PARTS = {"public_aggregate_only", "encrypted_reviewer_handoff_only"}


def _private_area(path: Path) -> Path:
    target = path.resolve()
    if (target == REPO or REPO in target.parents
            or any(part in SENSITIVE_PARTS for part in target.parts)):
        raise ValueError("FDA reviewer key/plaintext must remain outside Git/CI public folders")
    return target


def _read_hex_key(path: Path, *, private: bool) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 200:
        raise ValueError("FDA reviewer key source is missing or unsafe")
    if private:
        _private_area(path)
        if os.name != "posix":
            raise ValueError("Private key loading needs a verified POSIX owner-only filesystem")
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError("FDA private reviewer key must be readable only by its owner")
    text = path.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-fA-F0-9]{64}", text):
        raise ValueError("FDA reviewer key must be 32 raw bytes encoded as 64 hex digits")
    return bytes.fromhex(text)


def _exclusive_file(path: Path, value: bytes, *, private: bool) -> None:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600 if private else 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(value)


def create_local_keys(new_folder: Path) -> dict:
    """Explicit reviewer-only key creation, not suitable for a public runner."""
    if os.name != "posix":
        raise ValueError(
            "Generate recipient keys in a restricted POSIX/WSL private directory; "
            "this script cannot verify Windows ACLs."
        )
    folder = _private_area(new_folder)
    if folder.exists() or folder.is_symlink():
        raise FileExistsError("Private FDA recipient key destination must be NEW")
    folder.mkdir(mode=0o700, parents=True, exist_ok=False)
    folder.chmod(0o700)
    try:
        reviewer = X25519PrivateKey.generate()
        private_bytes = reviewer.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_bytes = reviewer.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        _exclusive_file(
            folder / PRIV, (private_bytes.hex() + "\n").encode("ascii"),
            private=True,
        )
        _exclusive_file(
            folder / PUB, (public_bytes.hex() + "\n").encode("ascii"),
            private=False,
        )
        if stat.S_IMODE((folder / PRIV).stat().st_mode) & 0o077:
            raise ValueError("Reviewer private key permissions are unsafe")
        return {
            "status": "FDA_RECIPIENT_PUBLIC_KEY_READY_PRIVATE_KEY_LOCALLY_HELD",
            "public_key_sha256": hashlib.sha256(public_bytes).hexdigest(),
            "private_key_ever_uploaded": False,
            "public_key_safe_to_share": True,
            "key_stored_in_github": False,
            "private_key_written_only_to_chosen_local_directory": True,
            "reviewer_responsible_for_local_backup_and_sync_controls": True,
            "reviewer_identity_authenticated": False,
            "original_fda_review_cycles_verified": 0,
        }
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline source-locked FDA visual-review recipient transfer"
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--create-local-recipient-keys", action="store_true")
    modes.add_argument("--encrypt-with-public-key", action="store_true")
    modes.add_argument("--decrypt-with-private-key", action="store_true")
    parser.add_argument("--new-private-key-folder", type=Path)
    parser.add_argument("--recipient-public-key-file", type=Path)
    parser.add_argument("--recipient-private-key-file", type=Path)
    parser.add_argument("--private-image-dir", type=Path)
    parser.add_argument("--private-batch1-manifest", type=Path)
    parser.add_argument("--private-batch2-manifest", type=Path)
    parser.add_argument("--encrypted-output", type=Path)
    parser.add_argument("--encrypted-input", type=Path)
    parser.add_argument("--new-private-decrypted-folder", type=Path)
    args = parser.parse_args()

    if args.create_local_recipient_keys:
        if not args.new_private_key_folder:
            raise ValueError("Explicit new private key folder required")
        report = create_local_keys(args.new_private_key_folder)
    elif args.encrypt_with_public_key:
        if any(x is None for x in (
            args.recipient_public_key_file, args.private_image_dir,
            args.private_batch1_manifest, args.private_batch2_manifest,
            args.encrypted_output,
        )):
            raise ValueError("FDA source images, manifests and public key required")
        public = _read_hex_key(args.recipient_public_key_file, private=False)
        source_paths = (
            args.private_image_dir.resolve(),
            args.private_batch1_manifest.resolve(),
            args.private_batch2_manifest.resolve(),
            args.recipient_public_key_file.resolve(),
        )
        target = args.encrypted_output.resolve()
        if (target in source_paths or
                any(target.is_relative_to(source) for source in source_paths)):
            raise ValueError("Encrypted output must be separate from source evidence")
        ciphertext, report = seal_for_recipient(
            args.private_image_dir,
            args.private_batch1_manifest,
            args.private_batch2_manifest,
            recipient_public_raw=public,
        )
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _exclusive_file(target, ciphertext, private=True)
    else:
        if any(x is None for x in (
            args.encrypted_input, args.recipient_private_key_file,
            args.new_private_decrypted_folder,
        )):
            raise ValueError("FDA encrypted input, reviewer key and private output required")
        raw = _read_hex_key(args.recipient_private_key_file, private=True)
        reviewer = X25519PrivateKey.from_private_bytes(raw)
        archive = args.encrypted_input.read_bytes()
        records = open_for_recipient(archive, recipient_private=reviewer)
        target = _private_area(args.new_private_decrypted_folder)
        if (target.exists() or target.is_symlink()
                or target == args.encrypted_input.resolve()
                or args.encrypted_input.resolve() in target.parents):
            raise ValueError("FDA private reviewer destination must be separate and new")
        target.mkdir(mode=0o700, parents=True, exist_ok=False)
        target.chmod(0o700)
        try:
            for name, content in records.items():
                dest = target / name
                dest.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                dest.parent.chmod(0o700)
                _exclusive_file(dest, content, private=True)
        except BaseException:
            shutil.rmtree(target, ignore_errors=True)
            raise
        report = {
            "status": "FDA_RECIPIENT_AUTHENTICATED_19_IMAGE_ARCHIVE_OPENED_LOCALLY_NOT_REVIEWED",
            "restored_source_pngs": 19,
            "restored_source_manifests": 2,
            "original_fda_review_cycles_verified": 0,
            "human_visual_reviews_completed": 0,
            "model_eligible_records": 0,
        }

    # No private key, original document URL, page identity, or decrypted
    # source data in normal stdout or public analytics.
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
