"""Conservative schema screening for candidate FDA action evidence.

This validates metadata only; it does not authenticate documents or promote
records to independently adjudicated outcomes.
"""
from __future__ import annotations
from datetime import date, datetime
from urllib.parse import urlparse
import re

_ID = re.compile(r"^(?:NDA|BLA|ANDA)[- ]?\d{5,6}$", re.I)
_SHA = re.compile(r"^[a-fA-F0-9]{64}$")


def screen_candidate(row: dict) -> dict:
    issues = []
    if not isinstance(row, dict):
        return {"status": "QUARANTINED", "issues": ["not_an_object"],
                "independently_verified": False, "model_eligible": False}
    if not _ID.fullmatch(str(row.get("application_id", ""))):
        issues.append("invalid_application_id")
    if not isinstance(row.get("submission_id"), str) or not row["submission_id"].strip():
        issues.append("missing_submission_id")
    if type(row.get("review_cycle")) is not int or row["review_cycle"] < 1:
        issues.append("invalid_review_cycle")
    if row.get("action_type") not in {"APPROVAL", "COMPLETE_RESPONSE", "OTHER", "UNRESOLVED"}:
        issues.append("invalid_action_type")
    for field in ("action_date", "retrieved_at"):
        try:
            value = row[field]
            if field == "action_date":
                date.fromisoformat(value)
            else:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError):
            issues.append("invalid_" + field)
    source = row.get("official_source_url")
    try:
        parsed = urlparse(source)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not (host == "fda.gov" or host.endswith(".fda.gov")):
            issues.append("non_official_source")
    except (ValueError, TypeError, AttributeError):
        issues.append("non_official_source")
    if not isinstance(row.get("document_title"), str) or not row["document_title"].strip():
        issues.append("missing_document_title")
    if not isinstance(row.get("evidence_locator"), str) or not row["evidence_locator"].strip():
        issues.append("missing_evidence_locator")
    digest = row.get("document_sha256")
    if digest is not None and (not isinstance(digest, str) or not _SHA.fullmatch(digest)):
        issues.append("invalid_document_sha256")
    return {"status": "CANDIDATE_METADATA_COMPLETE" if not issues else "QUARANTINED",
            "issues": issues, "independently_verified": False, "model_eligible": False,
            "note": "Metadata screening cannot authenticate FDA source bytes or adjudicate outcomes."}
