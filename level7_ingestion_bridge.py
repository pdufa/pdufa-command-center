"""Opt-in bridge from published source bytes to persistent Level 7 history.

No network requests or production database access. Caller must supply an exact
trial identity and immutable revision from the existing ingestion workflow.
"""
from __future__ import annotations
from level7_evidence import EvidenceLedger
from level7_published_snapshot import record_published_snapshot
from level7_store import EvidenceStore

def persist_published_snapshot(
    store: EvidenceStore, *, trial_id: str, relative_path: str,
    revision: str, content: bytes | None, retrieved_at: str,
    status: str = "unverified",
) -> bool:
    """Record a source snapshot. Return True only for a new source version."""
    if not trial_id.strip():
        raise ValueError("Exact trial identity required")
    ledger = EvidenceLedger()
    record = record_published_snapshot(
        ledger, trial_id=trial_id, relative_path=relative_path,
        revision=revision, content=content, retrieved_at=retrieved_at,
        status=status,
    )
    store.initialize()
    return store.add(record)
