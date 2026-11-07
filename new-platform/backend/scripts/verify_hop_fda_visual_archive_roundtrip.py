"""Run an ACTUAL FDA 19-PNG encrypted handoff dry run, with NO export.

Reuses the 19 private bitmaps regenerated from the pinned official FDA PDF
files by the isolated research workflow. Generates an ephemeral CSPRNG key,
encrypts in memory, decrypts/authenticates in memory, checks each restored
source image/manifest byte-for-byte, tests wrong-key authentication failure,
and irreversibly discards ciphertext and key on process exit.

Only aggregate integers and unreviewed-state flags are written to the
PUBLIC research count-only area. NO KEY, ciphertext, image or manifest is
uploaded. This is not durable reviewer storage or FDA adjudication.
"""
from __future__ import annotations

import argparse
import json
import secrets
from pathlib import Path

from app.hop_fda_visual_archive_crypto import decrypt_to_memory, pack


def verify_ephemeral_roundtrip(
    images: Path,
    first_manifest: Path,
    second_manifest: Path,
) -> dict:
    key = secrets.token_bytes(32)
    ciphertext, encrypt_audit = pack(
        images, first_manifest, second_manifest, key=key,
    )
    restored = decrypt_to_memory(ciphertext, key=key)
    if (
        set(restored) != {
            "manifests/batch1.json", "manifests/batch2.json",
            *("pages/" + entry.name for entry in images.iterdir())
        }
        or restored["manifests/batch1.json"] != first_manifest.read_bytes()
        or restored["manifests/batch2.json"] != second_manifest.read_bytes()
        or any(
            restored["pages/" + entry.name] != entry.read_bytes()
            for entry in images.iterdir()
        )
    ):
        raise ValueError("Recovered FDA reviewer bundle differs from private originals")

    from cryptography.exceptions import InvalidTag
    wrong_key = secrets.token_bytes(32)
    if wrong_key == key:
        raise ValueError("Unusable ephemeral key test")
    wrong_key_rejected = False
    try:
        decrypt_to_memory(ciphertext, key=wrong_key)
    except InvalidTag:
        wrong_key_rejected = True
    if not wrong_key_rejected:
        raise ValueError("Wrong private FDA decryption key was not rejected")
    if (
        encrypt_audit["encrypted_png_files"] != 19
        or len(restored) != 21
        or encrypt_audit["model_eligible_records"] != 0
    ):
        raise ValueError("FDA source package population was not exact")
    return {
        "status": "FDA_PRIVATE_VISUAL_ARCHIVE_EPHEMERAL_ROUNDTRIP_VERIFIED",
        "source_png_images_verified": 19,
        "private_original_manifests_verified": 2,
        "encrypted_archive_roundtrip_in_memory": True,
        "authenticated_decryption_recovered_original_bytes": True,
        "wrong_key_rejected": wrong_key_rejected,
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


def main() -> int:
    p = argparse.ArgumentParser(
        description="Actual FDA source-backed 19-page ephemeral AEAD handoff test"
    )
    p.add_argument("--private-image-dir", type=Path, required=True)
    p.add_argument("--private-batch1-manifest", type=Path, required=True)
    p.add_argument("--private-batch2-manifest", type=Path, required=True)
    p.add_argument("--public-counts-json", type=Path, required=True)
    args = p.parse_args()
    dest = args.public_counts_json.resolve()
    source_paths = (
        args.private_image_dir.resolve(),
        args.private_batch1_manifest.resolve(),
        args.private_batch2_manifest.resolve(),
    )
    if (
        dest in source_paths
        or any(dest in source.parents or source in dest.parents
               for source in source_paths)
        or "private_original_tables" in dest.parts
    ):
        raise ValueError("Aggregate FDA report must be separate from private evidence")
    audit = verify_ephemeral_roundtrip(
        args.private_image_dir,
        args.private_batch1_manifest,
        args.private_batch2_manifest,
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("x", encoding="utf-8") as handle:
        json.dump(audit, handle, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
