"""Offline FDA A/B encryption or recovery: no cloud upload and no key creation.

The three independent public keys must be verified and supplied from outside
Git/CI. Private keys are needed only for offline recovery; never pass them
in shell arguments or copy them into CI, logs, or Google Drive.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_private_encrypted_transfer import (
    ROLE, restore_private_fda_batches, seal_private_fda_batches,
)

REPOSITORY = Path(__file__).resolve().parents[3]


def _raw_key(path: Path, *, private: bool) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("FDA encryption key file must be an ordinary local file")
    full = path.resolve()
    if full == REPOSITORY or full.is_relative_to(REPOSITORY):
        raise ValueError("FDA recipient keys must not be stored in source control")
    if private and os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise ValueError("FDA role private key file must be owner-only")
    if path.stat().st_size > 1000:
        raise ValueError("FDA role key file is larger than raw X25519 key material")
    try:
        key = base64.b64decode(path.read_text(encoding="ascii").strip(), validate=True)
    except (ValueError, UnicodeError, base64.binascii.Error):
        raise ValueError("FDA role key file must contain base64-encoded raw X25519 bytes") from None
    if len(key) != 32:
        raise ValueError("FDA role key file must decode to exactly 32 bytes")
    return key


def main() -> int:
    p = argparse.ArgumentParser(description="Encrypt/recover private blank FDA research files")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--encrypt-offline", action="store_true")
    mode.add_argument("--recover-offline", action="store_true")
    p.add_argument("--source-folder", type=Path, required=True)
    p.add_argument("--new-output-folder", type=Path, required=True)
    p.add_argument("--first-role-key-file", type=Path, required=True)
    p.add_argument("--second-role-key-file", type=Path, required=True)
    p.add_argument("--custody-role-key-file", type=Path, required=True)
    args = p.parse_args()

    source, target = args.source_folder.resolve(), args.new_output_folder.resolve()
    if (source == REPOSITORY or source.is_relative_to(REPOSITORY)
            or target == REPOSITORY or target.is_relative_to(REPOSITORY)
            or "public_aggregate_only" in source.parts
            or "public_aggregate_only" in target.parts):
        raise ValueError("FDA reviewer archives belong only in private storage")
    paths = (
        args.first_role_key_file, args.second_role_key_file,
        args.custody_role_key_file,
    )
    if len({path.resolve() for path in paths}) != len(ROLE):
        raise ValueError("FDA independent role keys must use separate files")
    if args.encrypt_offline:
        public_keys = {
            role: _raw_key(path, private=False)
            for role, path in zip(ROLE, paths)
        }
        result = seal_private_fda_batches(source, target, public_keys)
    else:
        private_keys = {
            role: X25519PrivateKey.from_private_bytes(_raw_key(path, private=True))
            for role, path in zip(ROLE, paths)
        }
        result = restore_private_fda_batches(source, target, private_keys)
    # No source URLs, application IDs, source fingerprints or keys to stdout.
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
