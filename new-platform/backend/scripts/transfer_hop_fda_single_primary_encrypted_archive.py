"""Run single-primary FDA recipient-key archive locally; never upload.

This command requires a trusted primary reviewer's verified public key and
an independent custody public key to encrypt; their owner-only private keys
are used only for offline recovery. No key generation, app access or uploads.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_single_primary_encrypted_archive import (
    seal_single_primary_fda_archive, restore_single_primary_fda_archive,
)
from transfer_hop_fda_private_encrypted_archive import _raw_key

REPOSITORY = Path(__file__).resolve().parents[3]


def main() -> int:
    p = argparse.ArgumentParser(description="Offline encrypted single-primary FDA research handoff")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--encrypt-offline", action="store_true")
    mode.add_argument("--recover-offline", action="store_true")
    p.add_argument("--source-folder", type=Path, required=True)
    p.add_argument("--new-output-folder", type=Path, required=True)
    p.add_argument("--primary-role-key-file", type=Path, required=True)
    p.add_argument("--custody-role-key-file", type=Path, required=True)
    args = p.parse_args()
    source, dest = args.source_folder.resolve(), args.new_output_folder.resolve()
    if (source.is_relative_to(REPOSITORY) or dest.is_relative_to(REPOSITORY)
            or "public_aggregate_only" in source.parts
            or "public_aggregate_only" in dest.parts
            or args.primary_role_key_file.resolve() ==
                args.custody_role_key_file.resolve()):
        raise ValueError("FDA source, output and recipient keys must be private and separate")
    if args.encrypt_offline:
        keys = {
            "PRIMARY": _raw_key(args.primary_role_key_file, private=False),
            "CUSTODY": _raw_key(args.custody_role_key_file, private=False),
        }
        audit = seal_single_primary_fda_archive(source, dest, keys)
    else:
        keys = {
            "PRIMARY": X25519PrivateKey.from_private_bytes(
                _raw_key(args.primary_role_key_file, private=True)),
            "CUSTODY": X25519PrivateKey.from_private_bytes(
                _raw_key(args.custody_role_key_file, private=True)),
        }
        audit = restore_single_primary_fda_archive(source, dest, keys)
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
