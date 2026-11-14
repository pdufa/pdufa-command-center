"""Fail-closed readiness check for FDA source images in a PUBLIC repository.

The 19 page PNGs are ephemeral GitHub runner files. Never upload their
plaintext to a public GitHub artifact, PR, or committed repository file.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SHA = re.compile(r"[0-9a-f]{64}\Z")
PNG = re.compile(r"([0-9a-f]{64})_page_([0-9]{3})[.]png\Z")


def audit_private_visual_handoff(image_dir: Path, manifests: tuple[Path, Path]) -> dict:
    if not image_dir.is_dir() or image_dir.is_symlink() or len(manifests) != 2:
        raise ValueError("FDA visual source directory or manifest pair missing")
    expected = {}
    for path in manifests:
        if not path.is_file() or path.is_symlink():
            raise ValueError("FDA private page manifest missing")
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            raise ValueError("Invalid FDA private page manifest")
        for row in records:
            name = row.get("private_rendered_png_name")
            m = PNG.fullmatch(name) if isinstance(name, str) else None
            if (not m or m.group(1) != row.get("source_full_pdf_sha256")
                or int(m.group(2)) != row.get("pdf_page_index_zero_based")
                or row.get("model_eligible") is not False
                or row.get("human_visual_review_completed") is not False
                or name in expected):
                raise ValueError("Invalid or promoted FDA visual evidence")
            expected[name] = row["rendered_png_sha256"]
    actual = {p.name for p in image_dir.iterdir()}
    if set(expected) != actual or len(actual) != 19:
        raise ValueError("Expected exact source-locked 19 FDA PNGs")
    import hashlib
    for p in image_dir.iterdir():
        if not p.is_file() or p.is_symlink() or p.stat().st_size > 8_000_000:
            raise ValueError("FDA source image path not safe")
        body = p.read_bytes()
        if not body.startswith(b"\x89PNG\r\n\x1a\n") or hashlib.sha256(body).hexdigest() != expected[p.name]:
            raise ValueError("Rendered FDA PNG source changed")
    return {
        "status": "PRIVATE_FDA_VISUAL_HANDOFF_SOURCE_READY_NO_PUBLIC_EXPORT",
        "private_source_png_count": len(actual),
        "source_png_sha256_manifest_verified": True,
        "public_repository_plaintext_export_permitted": False,
        "secure_recipient_key_configured": False,
        "durable_encrypted_review_archive_created": False,
        "human_visual_reviews_completed": 0,
        "fda_review_cycles_independently_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }
