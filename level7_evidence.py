"""Level 7: deterministic, owner-operated evidence provenance ledger.

No network access, clinical inference, scoring, or production writes.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

EvidenceStatus = Literal["verified", "unverified", "missing", "inaccessible", "conflicting"]

@dataclass(frozen=True)
class EvidenceRecord:
    trial_id: str
    source_id: str
    source_url: str
    publisher: str
    document_date: str | None
    retrieved_at: str
    source_version: str
    sha256_digest: str | None
    status: EvidenceStatus
    notes: str = ""

    @property
    def identity(self) -> tuple[str, str, str]:
        return self.trial_id, self.source_id, self.source_version

def make_record(*, trial_id: str, source_id: str, source_url: str,
                publisher: str, source_version: str, content: bytes | None,
                status: EvidenceStatus = "unverified", document_date: str | None = None,
                retrieved_at: str | None = None, notes: str = "") -> EvidenceRecord:
    if not trial_id.strip() or not source_id.strip() or not source_version.strip():
        raise ValueError("Trial, source, and version identifiers are required")
    if status not in ("verified", "unverified", "missing", "inaccessible", "conflicting"):
        raise ValueError("Unknown evidence status")
    if status == "verified" and (content is None or not source_url or not publisher):
        raise ValueError("Verified evidence requires content, source URL and publisher")
    if status in ("missing", "inaccessible") and content is not None:
        raise ValueError("Unavailable evidence must not carry invented content")
    stamp = retrieved_at or datetime.now(timezone.utc).isoformat()
    if datetime.fromisoformat(stamp.replace("Z", "+00:00")).tzinfo is None:
        raise ValueError("retrieved_at must include a timezone")
    return EvidenceRecord(trial_id, source_id, source_url, publisher,
                          document_date, stamp, source_version,
                          sha256(content).hexdigest() if content is not None else None,
                          status, notes)

class EvidenceLedger:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], EvidenceRecord] = {}

    def add(self, record: EvidenceRecord) -> bool:
        if record.status not in ("verified", "unverified", "missing", "inaccessible", "conflicting"):
            raise ValueError("Unknown evidence status")
        prior = self._records.get(record.identity)
        if prior is not None:
            if prior != record:
                raise ValueError("Conflicting evidence for existing source version; create a new version")
            return False
        self._records[record.identity] = record
        return True

    def history(self, trial_id: str) -> list[EvidenceRecord]:
        return sorted((r for r in self._records.values() if r.trial_id == trial_id),
                      key=lambda r: (r.retrieved_at, r.source_id, r.source_version))

    def export_json(self, path: str | Path) -> None:
        destination = Path(path)
        destination.write_text(json.dumps([asdict(r) for r in self._records.values()],
                                          sort_keys=True, indent=2) + "\n", encoding="utf-8")
