"""Append-only research evidence audit ledger (local SQLite, no deployment implied).

No user-supplied attestation can mark evidence VERIFIED. This ledger stores
unverified submissions and rejected attempts for independent review later.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from pathlib import Path

from research.prediction_v1_1_evidence_intake import make_unverified_receipt


SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence_events (
 event_id INTEGER PRIMARY KEY AUTOINCREMENT,
 event_time TEXT NOT NULL,
 program_id TEXT NOT NULL,
 field_id TEXT NOT NULL,
 event_kind TEXT NOT NULL CHECK (event_kind IN ('RECEIVED_UNVERIFIED','REJECTED')),
 payload_sha256 TEXT NOT NULL,
 previous_event_sha256 TEXT,
 event_sha256 TEXT NOT NULL UNIQUE,
 receipt_json TEXT NOT NULL,
 payload_json TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS evidence_events_no_update
BEFORE UPDATE ON evidence_events BEGIN SELECT RAISE(ABORT,'append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_events_no_delete
BEFORE DELETE ON evidence_events BEGIN SELECT RAISE(ABORT,'append-only'); END;
"""


def connect_ledger(path: str | Path):
    conn = sqlite3.connect(str(path))
    conn.executescript(SCHEMA)
    return conn


def _json_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def append_submission(conn, record, catalog, cutoff=None, *, now=None):
    """Persist the receipt and raw submission; no clinical verification or score."""
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    for key in ("program_id", "field_id"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"{key} is required")
    receipt = make_unverified_receipt(record, catalog, cutoff)
    kind = "RECEIVED_UNVERIFIED" if receipt["accepted"] else "REJECTED"
    payload = _json_bytes(record)
    payload_hash = hashlib.sha256(payload).hexdigest()
    when = now or datetime.now(timezone.utc).isoformat()
    with conn:
        previous = conn.execute("SELECT event_sha256 FROM evidence_events ORDER BY event_id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else None
        envelope = {"time": when, "program_id": record["program_id"], "field_id": record["field_id"],
                    "kind": kind, "payload_sha256": payload_hash,
                    "previous_event_sha256": previous_hash, "receipt": receipt}
        event_hash = hashlib.sha256(_json_bytes(envelope)).hexdigest()
        cursor = conn.execute(
            "INSERT INTO evidence_events(event_time,program_id,field_id,event_kind,payload_sha256,previous_event_sha256,event_sha256,receipt_json,payload_json) VALUES (?,?,?,?,?,?,?,?,?)",
            (when, record["program_id"], record["field_id"], kind, payload_hash,
             previous_hash, event_hash, _json_bytes(receipt).decode(), payload.decode()))
    return {"event_id": cursor.lastrowid, "event_sha256": event_hash,
            "receipt": receipt, "audit_persisted": True, "independently_verified": False,
            "decision": "ABSTAIN"}


def audit_chain(conn):
    previous = None
    count = 0
    for event in conn.execute("SELECT event_time,program_id,field_id,event_kind,payload_sha256,previous_event_sha256,event_sha256,receipt_json,payload_json FROM evidence_events ORDER BY event_id"):
        when, program, field, kind, payload_hash, linked, digest, receipt_raw, payload_raw = event
        try:
            payload = json.loads(payload_raw)
            receipt = json.loads(receipt_raw)
        except (ValueError, TypeError):
            return {"valid": False, "checked": count, "reason": "invalid stored JSON"}
        if hashlib.sha256(_json_bytes(payload)).hexdigest() != payload_hash or linked != previous:
            return {"valid": False, "checked": count, "reason": "payload or chain mismatch"}
        envelope = {"time": when, "program_id": program, "field_id": field, "kind": kind,
                    "payload_sha256": payload_hash, "previous_event_sha256": linked, "receipt": receipt}
        if hashlib.sha256(_json_bytes(envelope)).hexdigest() != digest:
            return {"valid": False, "checked": count, "reason": "event digest mismatch"}
        previous = digest
        count += 1
    return {"valid": True, "checked": count, "last_event_sha256": previous}
