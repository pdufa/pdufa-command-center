"""Append-only, versioned scientific evidence candidate ledger.

The ledger is a review queue, NOT a mechanism for marking external sources
independently verified. Input must be manually reviewed outside this software.
No GET/POST fetches external URLs, grants FDA approval grades, or modifies scans.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import main
from .scientific_investigation_20 import NCT_PATTERN
from .scientific_readiness_grades import EXTERNAL_GATES

SCHEMA_VERSION = "evidence-ledger-append-only-v1"
MAX_RECORDS = 100
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
GATES = {item[0] for item in EXTERNAL_GATES}
TYPES = {
    "peer_reviewed_publication", "official_agency_document",
    "protocol_sap", "clinical_study_report", "institutional_summary", "other",
}
RELATIONSHIPS = {"supports", "contradicts", "context", "unresolved"}
REVIEW_STATUS = "pending_independent_review"

_HASH_FIELDS = (
    "id", "nct_id", "thread_id", "revision", "supersedes_id", "gate_id",
    "source_url", "source_type", "source_published_at", "claim_text",
    "relationship", "caution", "review_status", "recorded_by", "created_at",
)


def validate_public_https(url: str) -> str:
    """Link-only validation. The service NEVER follows a submitted URL."""
    if not isinstance(url, str) or not 1 <= len(url) <= 800 or url != url.strip():
        raise ValueError("Valid public HTTPS evidence URL required")
    try:
        split = urlsplit(url)
        host = split.hostname
        port = split.port
    except ValueError:
        raise ValueError("Invalid evidence URL") from None
    if (split.scheme != "https" or not host or split.username is not None
            or split.password is not None or split.fragment
            or port not in (None, 443)
            or any(ord(c) < 32 or ord(c) == 127 for c in url)):
        raise ValueError("Public HTTPS URL without credentials or fragment required")
    lower = host.lower().rstrip(".")
    if (lower in {"localhost", "metadata.google.internal"}
            or lower.endswith((".localhost", ".local", ".internal", ".test", ".invalid"))
            or "." not in lower):
        raise ValueError("Public HTTPS hostname required")
    try:
        ip = ipaddress.ip_address(lower)
    except ValueError:
        ip = None
    if ip is not None:
        # No literal IP addresses (including publicly routable) in citations.
        raise ValueError("Public DNS hostname required")
    if split.path.startswith("//"):
        raise ValueError("Invalid evidence URL path")
    return url


def _fields(item: main.ScientificEvidenceLedgerEntry) -> dict:
    return {
        "id": item.id, "nct_id": item.nct_id, "thread_id": item.thread_id,
        "revision": item.revision, "supersedes_id": item.supersedes_id,
        "gate_id": item.gate_id, "source_url": item.source_url,
        "source_type": item.source_type, "source_published_at": item.source_published_at,
        "claim_text": item.claim_text, "relationship": item.relationship,
        "caution": item.caution, "review_status": item.review_status,
        "recorded_by": item.recorded_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _hash(content: dict) -> str:
    canonical = json.dumps({key: content[key] for key in _HASH_FIELDS},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _entry(item: main.ScientificEvidenceLedgerEntry) -> dict:
    content = _fields(item)
    if _hash(content) != item.content_sha256:
        raise ValueError("Scientific evidence entry integrity mismatch")
    return {
        "id": item.id,
        "threadId": item.thread_id,
        "revision": item.revision,
        "supersedesId": item.supersedes_id,
        "gateId": item.gate_id,
        "sourceUrl": item.source_url,
        "sourceType": item.source_type,
        "sourcePublishedAt": item.source_published_at,
        "claimText": item.claim_text,
        "relationship": item.relationship,
        "caution": item.caution,
        "reviewStatus": item.review_status,
        "recordedBy": item.recorded_by,
        "recordedAt": content["created_at"],
        "contentSha256": item.content_sha256,
        "independentlyVerified": False,
        "canCountTowardReadiness": False,
    }


def pilot_candidates(nct_id: str) -> list[dict]:
    """Existing cited pilot manifests become candidates, not verified findings."""
    if nct_id != "NCT02142738":
        return []
    from .scientific_pilot_keynote024_results import keynote024_published_results
    source = keynote024_published_results()
    candidate = []
    for snapshot in source["analysis_snapshots"]:
        candidate.append({
            "gateId": "published_results",
            "sourceUrl": snapshot["source_url"],
            "sourceType": "peer_reviewed_publication",
            "sourcePublishedAt": snapshot.get("publication_date"),
            "title": snapshot["analysis_id"].replace("_", " "),
            "relationship": "context",
            "reviewStatus": "citation_identified_not_adjudicated",
            "caution": "Source-linked historical result; protocol, endpoint and population reconciliation pending.",
            "independentlyVerified": False,
            "canCountTowardReadiness": False,
        })
    for other in source["corroborating_sources"]:
        # FDA-staff-authored journal paper is NOT an FDA.gov decision record.
        source_type = ("peer_reviewed_publication" if
                       other["source_type"] == "fda_staff_authored_approval_summary"
                       else "institutional_summary")
        candidate.append({
            "gateId": ("official_regulatory" if
                       other["source_type"] == "fda_staff_authored_approval_summary"
                       else "published_results"),
            "sourceUrl": other["source_url"],
            "sourceType": source_type,
            "sourcePublishedAt": None,
            "title": other["source_type"].replace("_", " "),
            "relationship": "context",
            "reviewStatus": "citation_identified_not_adjudicated",
            "caution": other["scope_note"],
            "independentlyVerified": False,
            "canCountTowardReadiness": False,
        })
    assert len(candidate) == 5
    return candidate


def read_ledger(nct_id: str) -> dict:
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    with Session(main.ENGINE) as session:
        total = session.scalar(select(func.count()).select_from(
            main.ScientificEvidenceLedgerEntry).where(
                main.ScientificEvidenceLedgerEntry.nct_id == nct_id)) or 0
        items = session.scalars(
            select(main.ScientificEvidenceLedgerEntry).where(
                main.ScientificEvidenceLedgerEntry.nct_id == nct_id
            ).order_by(main.ScientificEvidenceLedgerEntry.created_at.desc(),
                       main.ScientificEvidenceLedgerEntry.id.desc()).limit(MAX_RECORDS)
        ).all()
        entries = [_entry(v) for v in items]
    candidates = pilot_candidates(nct_id)
    return {
        "nctId": nct_id,
        "ledgerSchemaVersion": SCHEMA_VERSION,
        "entryCount": total,
        "entriesShown": len(entries),
        "truncated": total > len(entries),
        "entries": entries,
        "identifiedSourceCandidates": candidates,
        "candidateCount": len(candidates),
        "externalGateStatuses": [
            {"gateId": gate_id, "label": label, "independentlyVerified": False,
             "status": "requires_independent_adjudication"}
            for gate_id, label, _ in EXTERNAL_GATES
        ],
        "verifiedGateCount": 0,
        "readinessGradesAutomaticallyPromoted": False,
        "note": ("Every saved item is an immutable candidate awaiting independent "
                 "scientific review. Candidate citations and submissions do NOT "
                 "automatically satisfy readiness gates or imply a drug's success."),
    }


def append_candidate(nct_id: str, data: dict) -> dict:
    """Append a reviewed-by-name *candidate*, never a 'verified' assertion.

    Corrections append a new numbered revision; originals are never overwritten.
    Unique DB constraints prevent two competing revisions of the same entry.
    """
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    gate = data["gateId"]
    kind = data["sourceType"]
    relationship = data["relationship"]
    if gate not in GATES or kind not in TYPES or relationship not in RELATIONSHIPS:
        raise ValueError("Unsupported evidence gate/source type/relationship")
    url = validate_public_https(data["sourceUrl"])
    now = datetime.now(timezone.utc)
    row_id = uuid.uuid4().hex
    prior_id = data.get("supersedesId")
    if prior_id is not None and (not isinstance(prior_id, str) or
                                not ID_PATTERN.fullmatch(prior_id)):
        raise ValueError("Invalid prior evidence entry identifier")
    with Session(main.ENGINE) as session:
        if session.get(main.FullTrialRecord, nct_id) is None:
            raise ValueError("Trial must already be archived in isolated review storage")
        if prior_id:
            prior = session.get(main.ScientificEvidenceLedgerEntry, prior_id)
            if prior is None or prior.nct_id != nct_id:
                raise ValueError("Prior evidence entry not in this exact trial")
            if _hash(_fields(prior)) != prior.content_sha256:
                raise ValueError("Prior evidence entry checksum invalid")
            child = session.scalars(select(main.ScientificEvidenceLedgerEntry.id).where(
                main.ScientificEvidenceLedgerEntry.supersedes_id == prior_id
            ).limit(1)).first()
            if child is not None:
                raise ValueError("Evidence revision already superseded")
            thread_id, revision = prior.thread_id, prior.revision + 1
        else:
            thread_id, revision = row_id, 1
        row = main.ScientificEvidenceLedgerEntry(
            id=row_id, nct_id=nct_id, thread_id=thread_id,
            revision=revision, supersedes_id=prior_id,
            gate_id=gate, source_url=url, source_type=kind,
            source_published_at=data.get("sourcePublishedAt"),
            claim_text=data["claimText"], relationship=relationship,
            caution=data["caution"],
            review_status=REVIEW_STATUS, recorded_by=data["recordedBy"],
            created_at=now, content_sha256="0"*64,
        )
        row.content_sha256 = _hash(_fields(row))
        session.add(row)
        # Constraint failure becomes a conflict, not a destructive overwrite.
        session.commit()
        return _entry(row)
