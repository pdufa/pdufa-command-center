"""Trusted-review workflow *proposal* for v1.1; fail-closed until identity is external.

Reviewer authorization is supplied by a trusted caller, never by a submission
payload. This module does not authenticate users, certify sources, or issue a
prediction. An authorization backend must be connected before production use.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from research.prediction_v1_1_audit_ledger import _json_bytes
from research.prediction_v1_1_submitter_binding import authorize_independent_review

REVIEW_SCHEMA = """
CREATE TABLE IF NOT EXISTS review_events (
 review_id INTEGER PRIMARY KEY AUTOINCREMENT,
 reviewed_at TEXT NOT NULL,
 evidence_event_id INTEGER NOT NULL,
 reviewer_principal TEXT NOT NULL,
 review_outcome TEXT NOT NULL CHECK (review_outcome IN ('APPROVE_PROVENANCE','REJECT_PROVENANCE','REQUEST_MORE_EVIDENCE')),
 source_bytes_verified INTEGER NOT NULL CHECK (source_bytes_verified IN (0,1)),
 publication_date_verified INTEGER NOT NULL CHECK (publication_date_verified IN (0,1)),
 identity_verified INTEGER NOT NULL CHECK (identity_verified IN (0,1)),
 rationale TEXT NOT NULL,
 previous_review_hash TEXT,
 review_hash TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS review_events_no_update
BEFORE UPDATE ON review_events BEGIN SELECT RAISE(ABORT,'append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_events_no_delete
BEFORE DELETE ON review_events BEGIN SELECT RAISE(ABORT,'append-only'); END;
"""


def initialize_review_ledger(conn):
    conn.executescript(REVIEW_SCHEMA)


def record_review(conn, *, evidence_event_id, reviewer_principal, outcome, checks, rationale,
                  trusted_identity=None, reviewed_at=None):
    """Record a review; does not promote evidence to independently VERIFIED.

    trusted_identity must be an object supplied by a future authenticated
    service. It is intentionally impossible to grant approval without it.
    """
    if trusted_identity is None or not getattr(trusted_identity, "is_authenticated", False):
        raise PermissionError("independent trusted reviewer authentication not connected")
    if getattr(trusted_identity, "principal", None) != reviewer_principal:
        raise PermissionError("reviewer principal does not match authenticated identity")
    if "evidence_reviewer" not in getattr(trusted_identity, "roles", ()):
        raise PermissionError("reviewer role required")
    # Reject unbound, cross-program and self-review before any write.
    authorize_independent_review(conn, evidence_event_id, trusted_identity)
    if outcome not in ("APPROVE_PROVENANCE","REJECT_PROVENANCE","REQUEST_MORE_EVIDENCE"):
        raise ValueError("invalid review outcome")
    if not isinstance(rationale, str) or not rationale.strip():
        raise ValueError("review rationale required")
    if not isinstance(checks, dict) or any(type(checks.get(k)) is not bool for k in ("source_bytes","publication_date","identity")):
        raise ValueError("all three independent checks must be explicit booleans")
    if outcome == "APPROVE_PROVENANCE" and not all(checks.values()):
        raise ValueError("all independent checks required for provenance approval")
    evidence = conn.execute("SELECT event_kind, payload_json FROM evidence_events WHERE event_id=?", (evidence_event_id,)).fetchone()
    if evidence is None or evidence[0] != "RECEIVED_UNVERIFIED":
        raise ValueError("review requires an accepted unverified submission")
    payload = json.loads(evidence[1])
    if payload.get("reviewer_id") == reviewer_principal:
        raise PermissionError("submitter cannot independently review own evidence")
    when = reviewed_at or datetime.now(timezone.utc).isoformat()
    with conn:
        previous = conn.execute("SELECT review_hash FROM review_events ORDER BY review_id DESC LIMIT 1").fetchone()
        previous_hash = previous[0] if previous else None
        envelope = {"reviewed_at": when, "evidence_event_id": evidence_event_id,
                    "reviewer_principal": reviewer_principal, "outcome": outcome,
                    "checks": checks, "rationale": rationale, "previous_review_hash": previous_hash}
        digest = hashlib.sha256(_json_bytes(envelope)).hexdigest()
        cursor = conn.execute("""INSERT INTO review_events
            (reviewed_at,evidence_event_id,reviewer_principal,review_outcome,
             source_bytes_verified,publication_date_verified,identity_verified,rationale,previous_review_hash,review_hash)
             VALUES (?,?,?,?,?,?,?,?,?,?)""",
             (when,evidence_event_id,reviewer_principal,outcome,
              int(checks["source_bytes"]),int(checks["publication_date"]),int(checks["identity"]),
              rationale,previous_hash,digest))
    return {"review_id": cursor.lastrowid, "review_hash": digest,
            "provenance_review_recorded": True, "independently_verified": False,
            "readiness": "NOT_READY", "decision": "ABSTAIN"}


def audit_review_chain(conn):
    """Check review event integrity, evidence references and previous-hash links.

    Hash chaining detects accidental or unauthorized in-place edits only if
    the expected head digest is independently anchored outside this database.
    """
    previous = None
    count = 0
    rows = conn.execute("""SELECT reviewed_at,evidence_event_id,reviewer_principal,
        review_outcome,source_bytes_verified,publication_date_verified,identity_verified,
        rationale,previous_review_hash,review_hash FROM review_events ORDER BY review_id""")
    for row in rows:
        (when, evidence_id, principal, outcome, source_ok, published_ok, identity_ok,
         rationale, linked, digest) = row
        if linked != previous:
            return {"valid": False, "checked": count, "reason": "review chain mismatch"}
        if not conn.execute("SELECT 1 FROM evidence_events WHERE event_id=? AND event_kind='RECEIVED_UNVERIFIED'", (evidence_id,)).fetchone():
            return {"valid": False, "checked": count, "reason": "review evidence missing or rejected"}
        envelope = {"reviewed_at": when, "evidence_event_id": evidence_id,
                    "reviewer_principal": principal, "outcome": outcome,
                    "checks": {"source_bytes": bool(source_ok), "publication_date": bool(published_ok),
                               "identity": bool(identity_ok)},
                    "rationale": rationale, "previous_review_hash": linked}
        if hashlib.sha256(_json_bytes(envelope)).hexdigest() != digest:
            return {"valid": False, "checked": count, "reason": "review digest mismatch"}
        previous = digest
        count += 1
    return {"valid": True, "checked": count, "last_review_hash": previous}
