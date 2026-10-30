"""Read-only v1.1 evidence status projection for a future authenticated API.

This module does not authenticate requests, access a deployed database, or
promote evidence to VERIFIED. The service layer must enforce access controls.
"""
from __future__ import annotations
import json
from research.prediction_v1_1_audit_ledger import audit_chain
from research.prediction_v1_1_review_workflow import audit_review_chain


def program_evidence_summary(conn, catalog, program_id):
    """Return draft-field status without treating review assertions as verification."""
    if not isinstance(program_id, str) or not program_id.strip():
        raise ValueError("program_id is required")
    evidence_integrity = audit_chain(conn)
    review_integrity = audit_review_chain(conn)
    if not evidence_integrity["valid"] or not review_integrity["valid"]:
        return {"program_id": program_id, "integrity": "FAILED", "readiness": "BLOCKED",
                "decision": "ABSTAIN", "fields": [], "independently_verified": 0}
    fields = []
    for field in catalog.get("fields", []):
        latest = conn.execute("""SELECT event_id,event_time,event_kind,receipt_json
             FROM evidence_events WHERE program_id=? AND field_id=?
             ORDER BY event_id DESC LIMIT 1""", (program_id, field["id"])).fetchone()
        if latest:
            event_id, received_at, kind, receipt_raw = latest
            receipt = json.loads(receipt_raw)
            status = receipt.get("status", "UNVERIFIED") if kind == "RECEIVED_UNVERIFIED" else "REJECTED"
            review = conn.execute("""SELECT review_outcome,reviewed_at FROM review_events
                WHERE evidence_event_id=? ORDER BY review_id DESC LIMIT 1""", (event_id,)).fetchone()
        else:
            event_id, received_at, status, review = None, None, "NOT_COLLECTED", None
        fields.append({"id": field["id"], "segment": field["segment"], "critical": field["critical"],
                       "mandatory": field["mandatory"], "status": status, "evidence_event_id": event_id,
                       "received_at": received_at, "latest_provenance_review": review[0] if review else None,
                       "reviewed_at": review[1] if review else None, "independently_verified": False})
    return {"program_id": program_id, "integrity": "CHECKED_LOCAL_CHAIN_ONLY",
            "catalog_status": catalog.get("status"), "defined_fields": len(fields),
            "proposed_slots": catalog.get("proposed_slots"), "independently_verified": 0,
            "readiness": "NOT_READY", "decision": "ABSTAIN", "fields": fields,
            "warning": "Research-only local projection; chain checks do not establish independent source verification or prediction validation."}
