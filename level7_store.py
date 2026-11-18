"""Opt-in SQLite persistence for Level 7 evidence records; no production DB access."""
from __future__ import annotations
from dataclasses import asdict
import json
import sqlite3
from pathlib import Path
from level7_evidence import EvidenceRecord, make_record

class EvidenceStore:
    def __init__(self, path: str | Path):
        self.path = str(path)

    def initialize(self):
        with sqlite3.connect(self.path) as db:
            db.execute('''CREATE TABLE IF NOT EXISTS level7_evidence (
                trial_id TEXT NOT NULL, source_id TEXT NOT NULL,
                source_version TEXT NOT NULL, record_json TEXT NOT NULL,
                PRIMARY KEY (trial_id, source_id, source_version))''')

    def add_many(self, records: list[EvidenceRecord]) -> dict:
        """All-or-nothing batch: a duplicate conflict rolls back the full report."""
        added, unchanged = 0, 0
        with sqlite3.connect(self.path) as db:
            for record in records:
                # Revalidate dataclass instances: callers can construct them
                # directly and bypass the make_record factory's status gate.
                make_record(
                    trial_id=record.trial_id, source_id=record.source_id,
                    source_url=record.source_url, publisher=record.publisher,
                    source_version=record.source_version,
                    content=None if record.sha256_digest is None else b"",
                    status=record.status, document_date=record.document_date,
                    retrieved_at=record.retrieved_at, notes=record.notes,
                )
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
