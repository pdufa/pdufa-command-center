"""Level 7 adapter for immutable published source snapshots.

Caller supplies bytes already retrieved by the existing source pipeline.
This module performs no network calls or writes to production.
"""
from __future__ import annotations
import re
from level7_evidence import EvidenceLedger, EvidenceRecord, make_record

_SHA = re.compile(r"[a-f0-9]{40}\\\Z")
_SAFE_PATH = re.compile(r"data/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\\\Z")

def record_published_snapshot(
    ledger: EvidenceLedger, *, trial_id: str, relative_path: str,
    revision: str, content: bytes | None, retrieved_at: str,
    publisher: str = "PDUFA published source snapshot",
    status: str = "unverified",
) -> EvidenceRecord:
    """Record a snapshot without claiming clinical or FDA verification."""
    if not _SAFE_PATH.fullmatch(relative_path) or any(
        segment in (".", "..") for segment in relative_path.split("/")
    ):
        raise ValueError("Expected safe data/ path")
    if revision != "main" and not _SHA.fullmatch(revision):
        raise ValueError("Expected exact 40-character immutable Git SHA or main")
    if revision == "main" and status == "verified":
        raise ValueError("Mutable main cannot establish an immutable verified revision")
    if content is None and status not in ("missing", "inaccessible"):
        raise ValueError("Absent snapshot requires missing or inaccessible status")
    if content is not None and status in ("missing", "inaccessible"):
        raise ValueError("Missing status cannot have snapshot bytes")
    source_url = (
        "https://raw.githubusercontent.com/pdufa/pdufa-command-center/"
        + revision + "/" + relative_path
    )
    record = make_record(
        trial_id=trial_id, source_id=relative_path,
        source_url=source_url, publisher=publisher,
        source_version=revision, content=content,
        status=status, retrieved_at=retrieved_at,
    )
    ledger.add(record)
    return record
