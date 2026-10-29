"""Research-only verification of a hash-chained prospective prediction ledger.

Chain validation detects edits only relative to an independently
anchored expected head. This module does not establish trusted time.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

_HASH = re.compile(r"[0-9a-f]{64}\Z")


def audit_ledger(path: str | Path, expected_head_sha256: str) -> tuple[bool, int]:
    """Verify every event and exact externally supplied chain head."""
    if not _HASH.fullmatch(expected_head_sha256):
        return False, 0
    path = Path(path)
    if not path.is_file():
        return False, 0
    previous = "0" * 64
    count = 0
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    return False, count
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    return False, count
                digest = entry.pop("entry_hash")
                if not isinstance(digest, str) or not _HASH.fullmatch(digest):
                    return False, count
                if entry.get("previous_hash") != previous:
                    return False, count
                canonical = json.dumps(entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
                if sha256(canonical).hexdigest() != digest:
                    return False, count
                previous = digest
                count += 1
    except (OSError, UnicodeError, ValueError, TypeError, KeyError):
        return False, count
    return count > 0 and previous == expected_head_sha256, count
