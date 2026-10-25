"""Isolated, immutable byte-for-byte archive of externally supplied source PDFs.

A URL is only a candidate locator. A captured PDF means a credentialed curator
supplied bytes that match a SHA-256 digest. It does NOT verify authorship,
document validity, reviewer identity, statistical analyses, clinical benefit,
FDA regulatory outcome, or any of the four independent scientific gates.

No server-side HTTP client, URL fetching, arbitrary PDF parsing or auto-scan.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import main
from .scientific_evidence_ledger import (
    GATES, _fields as ledger_fields, _hash as ledger_hash,
    pilot_candidates, require_registry_trial_identity, validate_public_https,
)
from .scientific_investigation_20 import NCT_PATTERN
from .scientific_reconciliation_worklist import reconciliation_worklist
from .scientific_stored_record import verified_record_from_archive

MAX_PDF_BYTES = 4 * 1024 * 1024
MAX_DOCUMENTS_PER_TRIAL = 8
SHA_PATTERN = re.compile(r"[a-f0-9]{64}\Z")
DOCUMENT_ID_PATTERN = re.compile(r"[a-f0-9]{32}\Z")
CAPTURE_STATUS = "byte_integrity_checked_not_independently_verified"


def _allowed_urls(session: Session, nct_id: str, gate_id: str) -> set[str]:
    urls = {
        item["sourceUrl"]
        for item in pilot_candidates(nct_id)
        if item["gateId"] == gate_id
    }
    for question in reconciliation_worklist(nct_id)["checks"]:
        if question["gateId"] == gate_id:
            urls.update(question["sourceUrls"])
    candidates = session.scalars(
        select(main.ScientificEvidenceLedgerEntry).where(
            main.ScientificEvidenceLedgerEntry.nct_id == nct_id,
            main.ScientificEvidenceLedgerEntry.gate_id == gate_id,
        )
    ).all()
    for item in candidates:
        if ledger_hash(ledger_fields(item)) != item.content_sha256:
            raise ValueError("Evidence candidate ledger integrity mismatch")
        urls.add(item.source_url)
    return urls


def _capture_meta(item: main.ScientificSourceDocument) -> dict:
    """Check every byte before allowing metadata into a review packet."""
    if len(item.payload) != item.byte_length:
        raise ValueError("Scientific document stored byte length mismatch")
    actual = hashlib.sha256(item.payload).hexdigest()
    if not hmac.compare_digest(item.sha256, actual):
        raise ValueError("Scientific document stored SHA-256 mismatch")
    if item.capture_status != CAPTURE_STATUS:
        raise ValueError("Scientific document unexpectedly marked verified")
    if not item.payload.startswith(b"%PDF-") or b"%%EOF" not in item.payload[-1024:]:
        raise ValueError("Scientific document PDF boundary mismatch")
    dt = item.captured_at
    when = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    return {
        "documentId": item.id,
        "nctId": item.nct_id,
        "gateId": item.gate_id,
        "sourceUrl": item.source_url,
        "sourceType": item.source_type,
        "filename": item.filename,
        "contentType": "application/pdf",
        "capturedBy": item.captured_by,
        "capturedAt": when.isoformat(),
        "byteLength": item.byte_length,
        "sha256": item.sha256,
        "captureStatus": CAPTURE_STATUS,
        "byteIntegrityChecked": True,
        "sourceAuthorshipVerified": False,
        "reviewerIdentityVerified": False,
        "documentContentScientificallyVerified": False,
        "canCountTowardReadiness": False,
        "access": "authenticated_review_only",
    }


def capture_document(nct_id: str, item: dict) -> dict:
    """Persist exact submitted PDF bytes (no URL request) with content hash."""
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    gate_id = item["gateId"]
    if gate_id not in GATES:
        raise ValueError("Unknown independent evidence gate")
    source_url = validate_public_https(item["sourceUrl"])
    require_registry_trial_identity(source_url, nct_id)
    declared_digest = item["sha256"]
    if not isinstance(declared_digest, str) or not SHA_PATTERN.fullmatch(declared_digest):
        raise ValueError("Lowercase SHA-256 digest required")
    encoded = item["contentBase64"]
    if not isinstance(encoded, str) or not 32 <= len(encoded) <= 4*((MAX_PDF_BYTES+2)//3):
        raise ValueError("Invalid PDF payload size")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError("Invalid strict base64 encoding") from None
    if not 32 <= len(raw) <= MAX_PDF_BYTES:
        raise ValueError("PDF must be within the isolated capture size limit")
    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
        raise ValueError("Unrecognized PDF signature or EOF marker")
    actual_digest = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual_digest, declared_digest):
        raise ValueError("PDF byte checksum does not match submitted SHA-256")

    with Session(main.ENGINE) as session:
        archive = session.get(main.FullTrialRecord, nct_id)
        if archive is None:
            raise ValueError("Trial not in isolated archive")
        verified_record_from_archive(nct_id, archive.payload_gzip, archive.sha256)
        if source_url not in _allowed_urls(session, nct_id, gate_id):
            raise ValueError("PDF source URL must match a known exact-trial, same-gate citation")
        count = session.scalar(select(func.count()).select_from(
            main.ScientificSourceDocument).where(
                main.ScientificSourceDocument.nct_id == nct_id
            )) or 0
        if count >= MAX_DOCUMENTS_PER_TRIAL:
            raise ValueError("Maximum captured PDF snapshots for this trial reached")
        found = session.scalar(select(main.ScientificSourceDocument.id).where(
            main.ScientificSourceDocument.nct_id == nct_id,
            main.ScientificSourceDocument.sha256 == actual_digest,
        ))
        if found is not None:
            raise ValueError("Exact PDF byte content is already archived for this trial")
        document_id = uuid.uuid4().hex
        row = main.ScientificSourceDocument(
            id=document_id, nct_id=nct_id, gate_id=gate_id,
            source_url=source_url, source_type=item["sourceType"],
            filename=nct_id+"_"+document_id+".pdf",
            captured_by=item["capturedBy"],
            captured_at=datetime.now(timezone.utc),
            sha256=actual_digest, byte_length=len(raw), payload=raw,
            capture_status=CAPTURE_STATUS,
        )
        session.add(row)
        session.commit()
        return _capture_meta(row)


def read_document_manifest(nct_id: str) -> dict:
    """Verify every stored document; never silently omit a tampered entry."""
    if not isinstance(nct_id, str) or not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT identifier required")
    with Session(main.ENGINE) as session:
        records = session.scalars(select(main.ScientificSourceDocument).where(
            main.ScientificSourceDocument.nct_id == nct_id
        ).order_by(main.ScientificSourceDocument.captured_at,
                   main.ScientificSourceDocument.id)).all()
        if len(records) > MAX_DOCUMENTS_PER_TRIAL:
            raise ValueError("Scientific document archive limit exceeded")
        snapshots = [_capture_meta(row) for row in records]
    return {
        "nctId": nct_id,
        "sourceDocumentCount": len(snapshots),
        "totalBytesStored": sum(row["byteLength"] for row in snapshots),
        "documents": snapshots,
        "allCapturedBytesRehashed": True,
        "independentSourceVerificationCompleted": False,
        "reviewerIdentityVerified": False,
        "scientificGradePromotionAllowed": False,
        "note": ("Hash equality proves stored byte consistency, not authentic "
                 "source provenance, clinical validity, FDA relevance or "
                 "independent scientific adjudication."),
    }


def get_captured_document(nct_id: str, doc_id: str) -> tuple[dict, bytes]:
    """Return verified PDF bytes only after API authentication and isolation checks."""
    if not NCT_PATTERN.fullmatch(nct_id) or not DOCUMENT_ID_PATTERN.fullmatch(doc_id):
        raise ValueError("Exact trial and document identity required")
    with Session(main.ENGINE) as session:
        archive = session.get(main.FullTrialRecord, nct_id)
        if archive is None:
            raise LookupError("Exact archived trial not found")
        verified_record_from_archive(nct_id, archive.payload_gzip, archive.sha256)
        row = session.get(main.ScientificSourceDocument, doc_id)
        if row is None or row.nct_id != nct_id:
            raise LookupError("Exact captured PDF not found for trial")
        return _capture_meta(row), bytes(row.payload)
