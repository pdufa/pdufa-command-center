"""Real-source FDA recipient-public-key envelope dry run, NO key or archive export.

Regenerates 19 PNGs in the private FDA research workflow, generates a
disposable X25519 receiver in memory, encrypts with its public key,
decrypts with its private key, verifies 19 PNG files and two manifests
byte-for-byte, and tests wrong-recipient/tampered-ciphertext rejection.

Only aggregate booleans/counts are published. No reviewer account, stored
private key, retained ciphertext or original FDA review-cycle label.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from app.hop_fda_visual_recipient_envelope import (
    open_for_recipient, seal_for_recipient,
)


def verify_ephemeral_recipient_envelope(
    images: Path,
    first_manifest: Path,
    second_manifest: Path,
) -> dict:
    receiver = X25519PrivateKey.generate()
    public = receiver.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    ciphertext, prepared = seal_for_recipient(
        images, first_manifest, second_manifest,
        recipient_public_raw=public,
    )
    recovered = open_for_recipient(
        ciphertext, recipient_private=receiver,
    )
    if (
        len(recovered) != 21
        or recovered["manifests/batch1.json"] != first_manifest.read_bytes()
        or recovered["manifests/batch2.json"] != second_manifest.read_bytes()
        or any(
            recovered.get("pages/" + file.name) != file.read_bytes()
            for file in images.iterdir()
        )
        or prepared["encrypted_source_png_files"] != 19
    ):
        raise ValueError("Source-backed FDA recipient decryption changed original evidence")

    wrong_recipient_rejected = False
    try:
        open_for_recipient(
            ciphertext,
            recipient_private=X25519PrivateKey.generate(),
        )
    except ValueError:
        wrong_recipient_rejected = True

    altered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])
    tampered_archive_rejected = False
    try:
        open_for_recipient(altered, recipient_private=receiver)
    except (InvalidTag, ValueError):
        tampered_archive_rejected = True

    if not wrong_recipient_rejected or not tampered_archive_rejected:
        raise ValueError("FDA recipient encryption accepted invalid credentials/evidence")

    return {
        "status": "FDA_19_REAL_SOURCE_IMAGES_EPHEMERAL_RECIPIENT_ENVELOPE_VERIFIED",
        "actual_pdf_derived_pngs_roundtrip_verified": 19,
        "original_source_manifests_roundtrip_verified": 2,
        "recipient_x25519_ecdh_kdf_aesgcm_verified": True,
        "wrong_recipient_private_key_rejected": wrong_recipient_rejected,
        "modified_encrypted_archive_rejected": tampered_archive_rejected,
        "private_recipient_key_exported": False,
        "encrypted_archive_exported": False,
        "original_source_pngs_exported": False,
        "durable_private_drive_upload_completed": False,
        "permanent_reviewer_public_key_registered": False,
        "independent_reviewer_authenticated": False,
        "human_visual_reviews_completed": 0,
        "independently_verified_original_fda_review_cycles": 0,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real 19-PNG ephemeral X25519 FDA source review transfer test"
    )
    parser.add_argument("--private-image-dir", type=Path, required=True)
    parser.add_argument("--private-batch1-manifest", type=Path, required=True)
    parser.add_argument("--private-batch2-manifest", type=Path, required=True)
    parser.add_argument("--public-counts-json", type=Path, required=True)
    args = parser.parse_args()
    destination = args.public_counts_json.resolve()
    source_paths = (
        args.private_image_dir.resolve(),
        args.private_batch1_manifest.resolve(),
        args.private_batch2_manifest.resolve(),
    )
    if (
        destination in source_paths
        or any(destination.is_relative_to(source) for source in source_paths)
        or "private_original_tables" in destination.parts
    ):
        raise ValueError("FDA aggregate output may not overlap private sources")

    result = verify_ephemeral_recipient_envelope(
        args.private_image_dir,
        args.private_batch1_manifest,
        args.private_batch2_manifest,
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump(result, output, sort_keys=True, indent=2)
        output.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
