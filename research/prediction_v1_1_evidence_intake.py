"""Research-only, fail-closed evidence intake contract for PDUFA v1.1.

No network fetch, source authentication, scoring, or FDA prediction is performed.
A URL or a user's assertion never constitutes independently verified evidence.
"""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlsplit
import hashlib
import json

STATUSES = {"MISSING", "UNVERIFIED", "NOT_APPLICABLE", "VERIFIED"}
REQUIRED = {"program_id", "field_id", "source_url", "source_document_sha256",
            "source_published_at", "observed_at", "evidence_excerpt",
            "applicability_rationale", "reviewer_id", "reviewed_at",
            "independent_review_confirmed", "status"}


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else None
    except ValueError:
        return None


def _valid_url(value):
    if not isinstance(value, str):
        return False
    try:
        url = urlsplit(value)
        return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password and not url.fragment
    except ValueError:
        return False


def validate_evidence_record(record, catalog, cutoff=None):
    """Return problems. A valid record is only well-formed, not independently verified."""
    if not isinstance(record, dict):
        return ["record must be an object"]
    errors = [f"missing {key}" for key in sorted(REQUIRED - record.keys())]
    if errors:
        return errors
    fields = {f["id"]: f for f in catalog.get("fields", [])}
    if record["field_id"] not in fields:
        errors.append("unknown field ID")
    if not isinstance(record["program_id"], str) or not record["program_id"].strip():
        errors.append("missing program identity")
    status = record["status"]
    if status not in STATUSES:
        errors.append("invalid status")
    if status == "VERIFIED":
        # Research-only endpoint cannot promote evidence to VERIFIED, even with self-asserted review flags.
        errors.append("VERIFIED requires a separate trusted reviewer workflow and immutable audit")
    if status == "NOT_APPLICABLE" and not str(record["applicability_rationale"]).strip():
        errors.append("not-applicable requires documented rationale")
    if status in {"UNVERIFIED", "VERIFIED"}:
        if not _valid_url(record["source_url"]):
            errors.append("source must be a valid HTTPS URL")
        digest = record["source_document_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            errors.append("source document hash must be a lowercase SHA-256")
        if not str(record["evidence_excerpt"]).strip():
            errors.append("evidence excerpt required")
    published = _timestamp(record["source_published_at"])
    observed = _timestamp(record["observed_at"])
    reviewed = _timestamp(record["reviewed_at"])
    if record["source_published_at"] is not None and published is None:
        errors.append("invalid source publication timestamp")
    if observed is None:
        errors.append("observed_at requires timezone-aware timestamp")
    if record["reviewed_at"] is not None and reviewed is None:
        errors.append("invalid review timestamp")
    if observed and reviewed and reviewed < observed:
        errors.append("review predates observation")
    if cutoff is not None:
        boundary = _timestamp(cutoff)
        if boundary is None:
            errors.append("invalid evidence cutoff")
        elif published is None or observed is None or published > boundary or observed > boundary:
            errors.append("evidence not proven available by cutoff")
    if record["independent_review_confirmed"] is True:
        errors.append("self-attested independent review is not accepted")
    return errors


def make_unverified_receipt(record, catalog, cutoff=None):
    errors = validate_evidence_record(record, catalog, cutoff)
    if errors:
        return {"accepted": False, "errors": errors, "decision": "ABSTAIN"}
    payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"accepted": True, "record_sha256": hashlib.sha256(payload).hexdigest(),
            "status": record["status"], "independently_verified": False,
            "audit_persisted": False, "readiness": "NOT_READY", "decision": "ABSTAIN"}
