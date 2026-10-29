"""Point-in-time historical FDA outcome labels; research-only, fail closed.

A missed PDUFA target is not itself a CRL, approval, or extension.
Labels require an attributable decision document and publication timestamp.
"""
from __future__ import annotations
from datetime import datetime

OUTCOMES = frozenset({"PASS", "CRL", "EXTENSION"})
REQUIRED = frozenset({"program_id", "outcome", "decision_at", "source_published_at",
                      "source_url", "source_document_sha256", "decision_document_id"})


def _date(value):
    if (not isinstance(value, str) or not value or len(value) > 64
            or value != value.strip() or "T" not in value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None
    except ValueError:
        return None


def validate_historical_label(label, *, evidence_cutoff=None):
    if not isinstance(label, dict):
        return ["label must be an object"]
    missing = REQUIRED - label.keys()
    if missing:
        return ["missing " + key for key in sorted(missing)]
    errors = []
    for key in ("program_id", "decision_document_id"):
        value = label[key]
        if (not isinstance(value, str) or not value or len(value) > 512
                or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)):
            errors.append("invalid " + key)
    if not isinstance(label["outcome"], str) or label["outcome"] not in OUTCOMES:
        errors.append("unknown or unresolved outcome; do not infer from target date")
    from research.prediction_v1_1_evidence_intake import _valid_url
    source_url = label["source_url"]
    if (not isinstance(source_url, str) or len(source_url) > 4000
            or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in source_url)
            or not _valid_url(source_url)):
        errors.append("source URL must be HTTPS")
    digest = label["source_document_sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        errors.append("invalid document SHA-256")
    decision = _date(label["decision_at"])
    published = _date(label["source_published_at"])
    if decision is None or published is None:
        errors.append("decision and publication timestamps must include timezone")
    elif published < decision:
        errors.append("source publication precedes claimed decision")
    if evidence_cutoff is not None:
        cutoff = _date(evidence_cutoff)
        if cutoff is None:
            errors.append("invalid evidence cutoff")
        elif decision and published and (decision <= cutoff or published <= cutoff):
            errors.append("outcome already known at evidence cutoff; prevent label leakage")
    return errors


def historical_label_receipt(label, *, evidence_cutoff=None):
    errors = validate_historical_label(label, evidence_cutoff=evidence_cutoff)
    return {
        "accepted_for_research_review": not errors,
        "errors": errors,
        "independently_verified": False,
        "prediction_readiness": "NOT_READY",
        "prediction_action": "ABSTAIN",
    }
