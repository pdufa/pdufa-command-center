"""Validate immutable, BLANK private FDA reviewer handoffs before archival.

The manifest is a cryptographic file-integrity checksum *inventory*, NOT
a signature, trusted timestamp, durable backup, human authentication, FDA
decision adjudication or a prediction-data approval. Keep it PRIVATE.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from pathlib import Path

from .hop_fda_private_review_batches import prepare_private_review_batches

FILENAME = re.compile(
    r"(AMBIGUOUS_ID|APPLICATION_ID)-([0-9]{2})_(FIRST|SECOND)_unreviewed[.]json\Z"
)
MANIFEST_NAME = "private_blank_fda_batch_custody_manifest.json"
STATUS = "PRIVATE_BLANK_FDA_BATCH_CHECKSUMS_NOT_DECISION_ADJUDICATION"
MAX_JSON_BYTES = 2_000_000


def private_blank_batch_inventory(directory: Path) -> dict:
    """Reconstruct and check every A/B source file; reveal no source rows."""
    folder = Path(directory)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("Private FDA batch directory must be an actual directory")
    if os.name == "posix" and stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("Private FDA batch directory permissions expose review data")

    files = {}
    for path in folder.iterdir():
        if path.name == MANIFEST_NAME:
            continue
        matched = FILENAME.fullmatch(path.name)
        if not matched or path.is_symlink() or not path.is_file():
            raise ValueError("Unrecognized or unsafe private FDA batch file")
        if os.name == "posix" and stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ValueError("Private FDA source file permissions expose review data")
        size = path.stat().st_size
        if not 0 < size <= MAX_JSON_BYTES:
            raise ValueError("Private FDA review file is empty or too large")
        content = path.read_bytes()
        try:
            records = json.loads(content)
        except (ValueError, UnicodeDecodeError):
            raise ValueError("Private FDA reviewer file is not valid JSON") from None
        if not isinstance(records, list) or not records:
            raise ValueError("Blank private reviewer batch must contain records")
        ident = matched.group(1) + "-" + matched.group(2)
        role = matched.group(3)
        if (ident, role) in files:
            raise ValueError("Duplicate FDA private reviewer batch/role")
        files[ident, role] = {
            "records": records,
            "name": path.name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "file_bytes": size,
        }

    ids = sorted({ident for ident, _ in files})
    if not ids or len(files) != 2 * len(ids):
        raise ValueError("Missing first/second FDA review batch pair")
    left, right = [], []
    for ident in ids:
        if (ident, "FIRST") not in files or (ident, "SECOND") not in files:
            raise ValueError("Both FDA review roles are required for every batch")
        left.extend(files[ident, "FIRST"]["records"])
        right.extend(files[ident, "SECOND"]["records"])

    # Reconstruct deterministic groups from the original source-lock metadata.
    # This also rejects populated reviewers, false model flags, repeated source
    # digests and A/B evidence inconsistencies.
    recomputed, audit = prepare_private_review_batches(
        left, right, max_references=20, expected_references=124,
        expected_groups=101,
    )
    if {x["batch_id"] for x in recomputed} != set(ids):
        raise ValueError("Private reviewer batches differ from source grouping")
    for item in recomputed:
        ident = item["batch_id"]
        if (files[ident, "FIRST"]["records"] != item["first_blank_reviewer_sources"]
                or files[ident, "SECOND"]["records"] != item["second_blank_reviewer_sources"]):
            raise ValueError("FDA private source group was split or reordered")
    manifest_files = [{
        "filename": files[key]["name"],
        "file_sha256": files[key]["sha256"],
        "file_bytes": files[key]["file_bytes"],
    } for key in sorted(files)]
    return {
        "status": STATUS,
        "file_count": len(manifest_files),
        "batch_count": len(ids),
        "published_letter_references": audit["published_letter_references"],
        "research_groups": audit["application_research_groups"],
        "reviewer_records_per_role": len(left),
        "files": manifest_files,
        "reviewer_identities_authenticated": False,
        "independently_verified_fda_review_cycles": 0,
        "complete_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "private_manifest_not_public_artifact": True,
        "note": (
            "SHA-256 detects changes only relative to a separately preserved, "
            "trusted manifest. It is not a digital signature, independent FDA "
            "review, or persistent archive."
        ),
    }


def save_private_blank_batch_manifest(directory: Path) -> dict:
    """Write first manifest exactly once. Never replace an existing baseline."""
    folder = Path(directory)
    baseline = folder / MANIFEST_NAME
    if baseline.exists() or baseline.is_symlink():
        raise FileExistsError("Cannot overwrite private FDA custody baseline")
    inventory = private_blank_batch_inventory(folder)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(baseline, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(inventory, out, indent=2, sort_keys=True)
        out.write("\n")
    return inventory


def verify_private_blank_batch_manifest(directory: Path) -> dict:
    """Verify stored source files against a previously saved private baseline."""
    folder = Path(directory)
    baseline = folder / MANIFEST_NAME
    if not baseline.is_file() or baseline.is_symlink():
        raise ValueError("Missing or unsafe private FDA custody manifest")
    if os.name == "posix" and stat.S_IMODE(baseline.stat().st_mode) & 0o077:
        raise ValueError("Private FDA custody manifest has unsafe permissions")
    try:
        saved = json.loads(baseline.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError):
        raise ValueError("Private FDA baseline JSON invalid") from None
    current = private_blank_batch_inventory(folder)
    if current != saved:
        raise ValueError("FDA private batch inventory differs from saved manifest")
    return {
        "status": "PRIVATE_BLANK_FDA_FILES_MATCH_BASELINE_NOT_ADJUDICATED",
        "source_batch_count": current["batch_count"],
        "private_role_files_integrity_checked": current["file_count"],
        "original_fda_review_cycles_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }
