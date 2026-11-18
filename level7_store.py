"""Opt-in SQLite persistence for Level 7 evidence records; no production DB access."""
from __future__ import annotations
from dataclasses import asdict
import json
import sqlite3
from pathlib import Path
from level7_evidence import EvidenceRecord

class EvidenceStore:
    def __init__(self, path: str | Path, *, read_only: bool = False):
        self.path = str(path)
        self.read_only = read_only

    def _connect(self):
        if self.read_only:
            return sqlite3.connect(Path(self.path).resolve().as_uri() + '?mode=ro', uri=True)
        return sqlite3.connect(self.path)

    def initialize(self):
        if self.read_only:
            raise PermissionError('Read-only evidence store cannot be initialized')
        with self._connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS level7_evidence (
                trial_id TEXT NOT NULL, source_id TEXT NOT NULL,
                source_version TEXT NOT NULL, record_json TEXT NOT NULL,
                PRIMARY KEY (trial_id, source_id, source_version))''')

    def add_many(self, records: list[EvidenceRecord]) -> dict:
        """All-or-nothing batch: a duplicate conflict rolls back the full report."""
        added, unchanged = 0, 0
        with sqlite3.connect(self.path) as db:
            for record in records:
                # Directly constructed records must satisfy persistence gates.
                if record.status not in (
                    "verified", "unverified", "missing", "inaccessible", "conflicting"
                ):
                    raise ValueError("Unknown evidence status")
                if record.status == "verified" and (
                    not record.sha256_digest or not record.source_url or not record.publisher
                ):
                    raise ValueError("Verified evidence requires digest, source URL and publisher")
                if record.status in ("missing", "inaccessible") and record.sha256_digest:
                    raise ValueError("Unavailable evidence cannot have a content digest")
                payload = json.dumps(asdict(record), sort_keys=True)
                row = db.execute(
                    'SELECT record_json FROM level7_evidence WHERE trial_id=? AND source_id=? AND source_version=?',
                    record.identity).fetchone()
                if row:
                    if row[0] != payload:
                        raise ValueError('Conflicting evidence for existing source version')
                    unchanged += 1
                else:
                    db.execute('INSERT INTO level7_evidence VALUES (?, ?, ?, ?)',
                               (*record.identity, payload))
                    added += 1
        return {"added": added, "unchanged": unchanged}

    def add(self, record: EvidenceRecord) -> bool:
        return bool(self.add_many([record])["added"])

    def history(self, trial_id: str) -> list[EvidenceRecord]:
        with sqlite3.connect(self.path) as db:
            rows = db.execute('SELECT record_json FROM level7_evidence WHERE trial_id=?', (trial_id,)).fetchall()
        return sorted((EvidenceRecord(**json.loads(row[0])) for row in rows),
                      key=lambda r: (r.retrieved_at, r.source_id, r.source_version))
