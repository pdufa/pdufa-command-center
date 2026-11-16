"""Offline byte-level integrity check for frozen historical evidence artifacts.

Caller supplies bytes from a trusted local source. No filesystem or network access.
Hash strings alone are insufficient to establish that evidence was actually frozen.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

_HASH = re.compile(r"[0-9a-f]{64}\Z")


def verify_frozen_artifacts(artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(artifacts, list):
        raise TypeError("Artifacts must be a list")
    errors: list[str] = []
    if not artifacts:
        errors.append("MISSING_ARTIFACTS")
    seen: set[str] = set()
    for index, artifact in enumerate(artifacts):
        prefix = f"ARTIFACT_{index}_"
        if not isinstance(artifact, dict):
            errors.append(prefix + "INVALID_RECORD")
            continue
        identifier = artifact.get("artifact_id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(prefix + "INVALID_ID")
        elif identifier in seen:
            errors.append(prefix + "DUPLICATE_ID")
        else:
            seen.add(identifier)
        expected = artifact.get("sha256")
        if not isinstance(expected, str) or not _HASH.fullmatch(expected):
            errors.append(prefix + "INVALID_HASH")
        payload = artifact.get("content")
        if not isinstance(payload, bytes):
            errors.append(prefix + "MISSING_BYTES")
        elif isinstance(expected, str) and _HASH.fullmatch(expected):
            if hashlib.sha256(payload).hexdigest() != expected:
                errors.append(prefix + "HASH_MISMATCH")
    return {
        "integrity_verified": not errors,
        "artifact_count": len(artifacts),
        "scientific_status": "NOT_VERIFIED",
        "scientific_score": None,
        "fda_prediction": "ABSTAIN",
        "errors": sorted(set(errors)),
    }
