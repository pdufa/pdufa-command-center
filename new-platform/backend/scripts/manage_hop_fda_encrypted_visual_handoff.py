"""Local/private FDA visual evidence archive command.

Encrypt on a controlled runner with a separately held key.
Decrypt only into a new private directory on the reviewer's computer.
Never print the key, page IDs, reviewer material or plaintext path lists.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.hop_fda_visual_archive_crypto import (
    decrypt_to_memory, external_key, pack,
)


def _write_exclusive(file: Path, contents: bytes) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(file, flags, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(contents)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Encrypt or decrypt 19 source-locked UNREVIEWED FDA visual pages"
    )
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--encrypt", action="store_true")
    modes.add_argument("--decrypt", action="store_true")
    p.add_argument("--private-image-dir", type=Path)
    p.add_argument("--private-batch1-manifest", type=Path)
    p.add_argument("--private-batch2-manifest", type=Path)
    p.add_argument("--encrypted-output", type=Path)
    p.add_argument("--encrypted-input", type=Path)
    p.add_argument("--private-decrypted-output-dir", type=Path)
    p.add_argument("--safe-aggregate-json", type=Path)
    args = p.parse_args()
    key = external_key()
    if args.encrypt:
        if any(v is None for v in (
            args.private_image_dir, args.private_batch1_manifest,
            args.private_batch2_manifest, args.encrypted_output,
        )) or args.encrypted_input or args.private_decrypted_output_dir:
            raise ValueError("Encrypted FDA source inputs/outputs must be specified")
        ciphertext, counts = pack(
            args.private_image_dir,
            args.private_batch1_manifest,
            args.private_batch2_manifest,
            key=key,
        )
        target = args.encrypted_output.resolve()
        if args.safe_aggregate_json and args.safe_aggregate_json.resolve() == target:
            raise ValueError("FDA encrypted artifact cannot overwrite count-only audit")
        _write_exclusive(target, ciphertext)
    else:
        if not args.encrypted_input or not args.private_decrypted_output_dir:
            raise ValueError("FDA encrypted input and private reviewer destination required")
        items = decrypt_to_memory(args.encrypted_input.read_bytes(), key=key)
        directory = args.private_decrypted_output_dir.resolve()
        repo_root = Path(__file__).resolve().parents[3]
        if (directory.exists() or directory == repo_root or
                repo_root in directory.parents or "public_aggregate_only" in directory.parts):
            raise ValueError("FDA review plaintext cannot be written to repository/public path")
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        directory.chmod(0o700)
        for name, body in items.items():
            target = directory / name
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.parent.chmod(0o700)
            _write_exclusive(target, body)
        counts = {
            "status": "FDA_VISUAL_REVIEW_BUNDLE_AUTHENTICATED_NOT_REVIEWED",
            "source_png_files": 19,
            "human_visual_reviews_completed": 0,
            "fda_review_cycles_independently_verified": 0,
            "model_eligible_records": 0,
            "prediction_probability": None,
        }
    if args.safe_aggregate_json:
        _write_exclusive(
            args.safe_aggregate_json.resolve(),
            (json.dumps(counts, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
