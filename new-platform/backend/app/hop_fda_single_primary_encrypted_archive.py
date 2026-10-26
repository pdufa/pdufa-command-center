"""Offline TWO-role encrypted handoff: one FDA primary reviewer + custodian.

No second reviewer key, no automatic Drive upload, no keys generated or stored.
Only seven BLANK PRIMARY research packets and one encrypted checksum
inventory are accepted. Signed independent FDA action verification remains zero.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from .hop_fda_private_encrypted_transfer import (
    MAX_RAW_BYTES, _private_target, _put_private, _role_for,
    open_fda_file, seal_fda_file,
)
from .hop_fda_single_primary_review import prepare_single_primary_batches

ROLE = ("PRIMARY", "CUSTODY")
MANIFEST = "private_single_primary_custody_manifest.json"
STATUS = "UNREVIEWED_SINGLE_PRIMARY_FDA_ENCRYPTED_HANDOFF_NOT_ADJUDICATED"
FILE = re.compile(
    r"(AMBIGUOUS_ID|APPLICATION_ID)-[0-9]{2}_PRIMARY_unreviewed[.]json\Z"
)


def _safe_private_folder(folder: Path) -> list[Path]:
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("FDA primary source must be an actual private directory")
    if os.name == "posix" and stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("FDA primary source directory must be owner-only")
    records = sorted(folder.iterdir())
    if (len(records) != 7
            or any(not x.is_file() or x.is_symlink() or not FILE.fullmatch(x.name)
                   or not 0 < x.stat().st_size <= MAX_RAW_BYTES for x in records)):
        raise ValueError("Exactly seven blank primary FDA review files are required")
    if os.name == "posix" and any(stat.S_IMODE(x.stat().st_mode) & 0o077 for x in records):
        raise ValueError("FDA primary source files must be owner-only")
    return records


def _inventory(folder: Path) -> dict:
    """Revalidate the seven immutable source-locked blank research batches."""
    files = _safe_private_folder(folder)
    source_rows, by_name = [], {}
    for path in files:
        raw = path.read_bytes()
        try:
            rows = json.loads(raw)
        except (UnicodeError, ValueError):
            raise ValueError("FDA primary source worksheet is not valid JSON") from None
        if not isinstance(rows, list) or not rows:
            raise ValueError("FDA primary worksheet missing source references")
        source_rows.extend(rows)
        by_name[path.name] = {
            "filename": path.name, "file_sha256": hashlib.sha256(raw).hexdigest(),
            "file_bytes": len(raw), "rows": rows,
        }
    batches, audit = prepare_single_primary_batches(
        source_rows, expected_references=124, expected_groups=101,
    )
    if len(batches) != 7:
        raise ValueError("FDA first-only research batch count must be seven")
    if {
        b["batch_id"] + "_PRIMARY_unreviewed.json" for b in batches
    } != set(by_name):
        raise ValueError("FDA primary batch IDs differ from sealed research cohort")
    for batch in batches:
        key = batch["batch_id"] + "_PRIMARY_unreviewed.json"
        if by_name[key]["rows"] != batch["primary_blank_source_rows"]:
            raise ValueError("FDA source reference moved or regrouped in primary archive")
    return {
        "status": STATUS,
        "review_mode": "SINGLE_PRIMARY_UNREVIEWED",
        "primary_role_file_count": 7,
        "published_letter_references": audit["published_letter_references"],
        "research_groups": audit["research_group_count"],
        "files": [
            {key: item[key] for key in ("filename", "file_sha256", "file_bytes")}
            for item in (by_name[path.name] for path in files)
        ],
        "reviewer_authenticated": False,
        "independent_original_fda_review_cycles_verified": 0,
        "complete_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "note": (
            "Encrypted local checksum inventory is not external provenance, "
            "authenticated FDA review, a signed artifact or durable storage."
        ),
    }


def _two_distinct_public_keys(keys: dict[str, bytes]) -> None:
    if (not isinstance(keys, dict) or set(keys) != set(ROLE)
            or any(not isinstance(x, bytes) or len(x) != 32 for x in keys.values())
            or keys["PRIMARY"] == keys["CUSTODY"]):
        raise ValueError("Two different verified public X25519 recipient keys required")


def seal_single_primary_fda_archive(
    source: Path, dest: Path, recipient_keys: dict[str, bytes],
) -> dict:
    """Seal seven private primary files plus custody manifest; no upload."""
    source = Path(source).resolve()
    dest = _private_target(dest, forbidden=source)
    _two_distinct_public_keys(recipient_keys)
    baseline = _inventory(source)
    if _role_for(MANIFEST) != "CUSTODY":
        raise ValueError("FDA custody encryption role mismatch")
    dest.mkdir(parents=True, mode=0o700)
    try:
        for entry in baseline["files"]:
            filename = entry["filename"]
            if _role_for(filename) != "PRIMARY":
                raise ValueError("FDA source reviewer role unexpectedly changed")
            sealed = seal_fda_file(
                (source / filename).read_bytes(), filename=filename,
                recipient_public_raw=recipient_keys["PRIMARY"],
            )
            _put_private(dest / (filename + ".fdaenc"), sealed)
        manifest = (json.dumps(baseline, sort_keys=True, indent=2) + "\n").encode()
        _put_private(dest / (MANIFEST + ".fdaenc"), seal_fda_file(
            manifest, filename=MANIFEST,
            recipient_public_raw=recipient_keys["CUSTODY"],
        ))
    except BaseException:
        shutil.rmtree(dest)
        raise
    return {
        "status": "EIGHT_LOCAL_ENCRYPTED_PRIMARY_PACKETS_NOT_UPLOADED",
        "primary_encrypted_packets": 7,
        "encrypted_custody_manifests": 1,
        "second_reviewer_packets": 0,
        "independent_fda_review_cycles_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }


def restore_single_primary_fda_archive(
    archive: Path, dest: Path, recipient_keys: dict[str, X25519PrivateKey],
) -> dict:
    """Prove offline recovery and checksum integrity, not stored-copy recovery."""
    archive = Path(archive).resolve()
    dest = _private_target(dest, forbidden=archive)
    if (not isinstance(recipient_keys, dict) or set(recipient_keys) != set(ROLE)
            or any(not isinstance(x, X25519PrivateKey)
                   for x in recipient_keys.values())):
        raise ValueError("Both primary and custodian private keys required")
    if archive.is_symlink() or not archive.is_dir():
        raise ValueError("FDA encrypted archive source directory missing")
    packages = sorted(archive.iterdir())
    if (len(packages) != 8
            or any(not p.is_file() or p.is_symlink()
                   or not p.name.endswith(".fdaenc")
                   or not (FILE.fullmatch(p.name[:-7])
                           or p.name == MANIFEST + ".fdaenc")
                   for p in packages)):
        raise ValueError("FDA one-reviewer encrypted package set incomplete")
    dest.mkdir(parents=True, mode=0o700)
    try:
        saved = None
        for path in packages:
            name = path.name[:-7]
            role = _role_for(name)
            plaintext = open_fda_file(
                path.read_bytes(), filename=name,
                recipient_private=recipient_keys[role],
            )
            if role == "CUSTODY":
                try:
                    saved = json.loads(plaintext)
                except (ValueError, UnicodeError):
                    raise ValueError("FDA private checksum baseline malformed") from None
            else:
                _put_private(dest / name, plaintext)
        actual = _inventory(dest)
        if saved != actual:
            raise ValueError("FDA restored source SHA or identity differs from custody")
    except BaseException:
        shutil.rmtree(dest)
        raise
    return {
        "status": "LOCAL_EIGHT_FILE_FDA_PRIMARY_RESTORE_VERIFIED_NOT_UPLOADED",
        "primary_source_files_restored": 7,
        "second_reviewer_files_restored": 0,
        "independent_fda_review_cycles_verified": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }
