#!/usr/bin/env python3
"""Validate source provenance before scientific review; no automated verification claims."""
from datetime import date
from urllib.parse import urlparse

ALLOWED_TYPES = {"trial_registry", "trial_results", "regulatory", "company_release", "publication"}
REQUIRED = {"nct", "source_type", "url", "document_date", "accessed_date", "evidence_excerpt", "reviewer", "phase"}


def validate_evidence(record):
    if not isinstance(record, dict):
        raise ValueError("Evidence must be an object")
    missing = REQUIRED - record.keys()
    if missing:
        raise ValueError("Missing provenance fields: " + ", ".join(sorted(missing)))
    nct = record["nct"]
    if not isinstance(nct, str) or not nct.startswith("NCT") or not nct[3:].isdigit():
        raise ValueError("Invalid NCT identifier")
    if record["source_type"] not in ALLOWED_TYPES:
        raise ValueError("Unknown source type")
    url = record["url"]
    if not isinstance(url, str):
        raise ValueError("Invalid source URL")
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Source must be an HTTPS URL without credentials")
    for field in ("document_date", "accessed_date"):
        value = record[field]
        if not isinstance(value, str):
            raise ValueError(f"Invalid {field}")
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError()
        except ValueError as exc:
            raise ValueError(f"Invalid {field}") from exc
    if record["document_date"] > record["accessed_date"]:
        raise ValueError("Document date cannot follow access date")
    for field in ("evidence_excerpt", "reviewer", "phase"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"Missing {field}")
    if record.get("verification_status", "pending") != "pending":
        raise ValueError("Provenance validation cannot certify evidence")
    if record.get("prediction") is not None or record.get("adjudication") is not None:
        raise ValueError("Evidence intake cannot contain predictions or adjudications")
    return {"nct": nct, "provenance_complete": True, "scientifically_verified": False, "verification_status": "pending"}
