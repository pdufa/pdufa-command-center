"""Audit actual FDA HTTPS original-byte capture receipts, never train on them.

A source PDF's SHA-256 and reviewed page identify *captured bytes*; neither
prove the PDF's original public-availability date nor retrospectively
adjudicate a complete FDA application review cycle. This register never
returns model-clearance flags, regardless of case count or caller assertions.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import zipfile

from .hop_primary_action_letter_samples import (
    _SAMPLE_FILE, _url_ok,
)

_RECEIPTS = Path(__file__).parent / "research_sources" / "hop_fda_original_byte_capture_receipts.json"
_SCHEMA = "hop-fda-original-byte-provenance-receipts-v1"
_HASH = re.compile(r"[a-f0-9]{64}\Z")
_TEXT_CHECKS = frozenset({
    "FIRST_PAGE_EXTRACTABLE_AND_LAST_SIGNATURE_PAGE_EXTRACTABLE",
    "FIRST_PAGE_IMAGE_ONLY_VISUALLY_RENDERED_AND_LAST_SIGNATURE_PAGE_EXTRACTABLE",
})


def _strict_date(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed if parsed.isoformat() == value else None
    except ValueError:
        return None


def _utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
        if (dt.tzinfo is None or dt.utcoffset() is None
                or dt.utcoffset().total_seconds() != 0
                or dt.isoformat(timespec="seconds") != value):
            return None
        return dt
    except ValueError:
        return None


def _blocked(as_of, compiled):
    return {
        "status": "CAPTURE_RECEIPTS_NOT_AVAILABLE_AT_AS_OF",
        "asOf": as_of.isoformat(),
        "capturedPdfRecords": 0,
        "records": [],
        "originalPdfShaVerifiedFromDownloadedArtifact": False,
        "sourceReviewCycleIndependentlyCertified": False,
        "independentlyVerifiedModelCycles": 0,
        "historicalRealBacktests": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "blockers": ["CAPTURE_OCCURRED_AFTER_THIS_RESEARCH_SNAPSHOT"],
    }


def audit_real_fda_capture_receipts(receipts: dict, letters: dict, *, as_of: date) -> dict:
    """Validate captured PDF digests and traceability against original source IDs."""
    if type(as_of) is not date:
        raise ValueError("Research cutoff must be an exact date")
    if not isinstance(receipts, dict) or receipts.get("schema_version") != _SCHEMA:
        raise ValueError("Unknown original PDF capture receipt schema")
    compiled = _strict_date(receipts.get("research_compiled_on"))
    if compiled is None:
        raise ValueError("Original source capture has no valid research date")
    if as_of < compiled:
        return _blocked(as_of, compiled)
    if (receipts.get("status") !=
            "REAL_ORIGINAL_PDF_BYTES_CAPTURED_NOT_INDEPENDENT_CYCLE_ADJUDICATION"
            or receipts.get("model_eligible_records") != 0
            or receipts.get("independent_real_backtest_cases") != 0
            or receipts.get("approval_probability") is not None):
        raise ValueError("Captured bytes must not clear model research gates")
    session = receipts.get("source_capture")
    if not isinstance(session, dict):
        raise ValueError("Exact source capture session required")
    if (type(session.get("github_workflow_run_id")) is not int
            or type(session.get("github_artifact_id")) is not int
            or session["github_workflow_run_id"] < 1
            or session["github_artifact_id"] < 1
            or type(session.get("artifact_retention_days")) is not int
            or not 1 <= session["artifact_retention_days"] <= 90
            or session.get("original_fda_pdf_files_persisted_in_git") is not False
            or session.get("capture_method") != "EXACT_ALLOWLISTED_TLS_HTTPS_NO_REDIRECT"
            or not isinstance(session.get("verification_note"), str)
            or not session["verification_note"].strip()
            or not _HASH.fullmatch(session.get("artifact_sha256", ""))):
        raise ValueError("Invalid source capture artifact provenance")
    expected_artifact_url = (
        "https://github.com/pdufa/pdufa-command-center/actions/runs/"
        f"{session['github_workflow_run_id']}/artifacts/"
        f"{session['github_artifact_id']}"
    )
    if session.get("github_artifact_url") != expected_artifact_url:
        raise ValueError("FDA capture artifact provenance URL mismatch")
    if session.get("tool") != "new-platform/backend/scripts/capture_hop_fda_original_https.py":
        raise ValueError("Unrecognized source capture program")

    if (not isinstance(letters, dict) or
            letters.get("schema_version") != "hop-fda-primary-action-letter-samples-v1"
            or not isinstance(letters.get("letters"), list)
            or len(letters["letters"]) != 2):
        raise ValueError("Matching source-authority FDA letter research register required")
    truth = {row["record_id"]: row for row in letters["letters"]}
    if len(truth) != 2:
        raise ValueError("Duplicate original FDA letter identity")
    rows = receipts.get("receipts")
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError("Exactly two original PDF capture records expected")
    records = []
    seen = set()
    seen_digests = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid PDF capture record object")
        identity = row.get("record_id")
        if identity not in truth or identity in seen:
            raise ValueError("PDF capture record cannot transfer across exact source identities")
        seen.add(identity)
        original = truth[identity]
        if (row.get("original_url") != original.get("original_document_url")
                or not _url_ok(row.get("original_url"))
                or row.get("document_reference_id") != original.get("document_reference_id")
                or row.get("fda_action_date_from_signature_page") != original.get("signature_date_observed")
                or row.get("http_status") != 200
                or row.get("redirected") is not False
                or row.get("content_type") != "application/pdf"):
            raise ValueError("Original FDA PDF source/signature/reference mismatch")
        captured = _utc(row.get("retrieval_observed_at_utc"))
        if captured is None or captured.date() != compiled:
            raise ValueError("Document capture time must match dated research snapshot")
        size = row.get("response_byte_length")
        digest = row.get("pdf_sha256")
        if (type(size) is not int or not 1024 <= size <= 20 * 1024 * 1024
                or not isinstance(digest, str) or not _HASH.fullmatch(digest)
                or digest in seen_digests):
            raise ValueError("Original PDF byte length/hash missing or duplicate")
        seen_digests.add(digest)
        if (type(row.get("pdf_pages")) is not int or row["pdf_pages"] < 2
                or row["pdf_pages"] > 500
                or row.get("source_document_text_check") not in _TEXT_CHECKS
                or not isinstance(row.get("first_page_application_observed"), str)
                or original["application_id"][3:] not in row["first_page_application_observed"]
                or row.get("first_page_action_observed") != original["document_action_heading"]
                or not isinstance(row.get("http_last_modified_header"), str)
                or not isinstance(row.get("http_etag"), str)
                or not row["http_last_modified_header"].strip()
                or not row["http_etag"].strip()):
            raise ValueError("Inspected PDF source page or response metadata inconsistent")
        if (row.get("original_fda_pdf_first_publication_date_verified") is not None
                or row.get("independently_adjudicated_fda_review_cycle") is not False
                or row.get("eligible_for_model_training") is not False):
            raise ValueError("PDF hash cannot certify publication date or training eligibility")
        records.append({
            "recordId": identity,
            "officialUrl": row["original_url"],
            "pdfSha256": digest,
            "capturedBytes": size,
            "capturedPageCount": row["pdf_pages"],
            "capturedAtUtc": captured.isoformat(timespec="seconds"),
            "sourceDocumentReference": row["document_reference_id"],
            "signedFdaActionDate": row["fda_action_date_from_signature_page"],
            "htmlLastModifiedIsFirstPublication": False,
            "httpLastModifiedHeader": row["http_last_modified_header"],
            "pdfFirstPublicDate": None,
            "exactCycleIndependentReviewerCertified": False,
            "modelEligible": False,
        })
    if seen != set(truth):
        raise ValueError("Original PDF capture provenance roster incomplete")
    return {
        "status": "FDA_ORIGINAL_PDF_BYTES_FINGERPRINTED_RESEARCH_ONLY",
        "asOf": as_of.isoformat(),
        "capturedPdfRecords": 2,
        "records": sorted(records, key=lambda row: row["recordId"]),
        "captureWorkflowRunId": session["github_workflow_run_id"],
        "captureArtifactId": session["github_artifact_id"],
        "artifactUrl": expected_artifact_url,
        "artifactZipSha256": session["artifact_sha256"],
        "artifactRetentionDays": session["artifact_retention_days"],
        "artifactAvailabilityNow": "NOT_CHECKED",
        "sourceBytesCommittedToRepository": False,
        "sourceReviewCycleIndependentlyCertified": False,
        "independentlyVerifiedModelCycles": 0,
        "historicalRealBacktests": 0,
        "approvalProbability": None,
        "trainingAuthorized": False,
        "blockers": [
            "FIRST_FDA_DOCUMENT_PUBLICATION_DATE_UNKNOWN",
            "REVIEW_CYCLE_INDEPENDENT_ADJUDICATION_MISSING",
            "PDUFA_REVISION_HISTORY_NOT_RECONCILED",
            "PREDECISION_FEATURE_SNAPSHOT_MISSING",
            "HISTORICAL_COHORT_DENOMINATOR_NOT_VERIFIED",
            "NO_MODEL_BACKTEST_OR_CALIBRATION",
        ],
    }


def load_real_fda_capture_receipts(*, as_of: date) -> dict:
    return audit_real_fda_capture_receipts(
        json.loads(_RECEIPTS.read_text(encoding="utf-8")),
        json.loads(_SAMPLE_FILE.read_text(encoding="utf-8")),
        as_of=as_of,
    )


def verify_source_artifact_zip(
    archive_bytes: bytes, receipts: dict,
) -> dict:
    """Independently recompute artifact, PDF and capture-report digests.

    Validation of *actual* contained bytes is not review-cycle adjudication
    or proof a PDF was publicly available on its action date.
    """
    if not isinstance(archive_bytes, bytes):
        raise ValueError("GitHub artifact ZIP must contain binary bytes")
    if hashlib.sha256(archive_bytes).hexdigest() != receipts["source_capture"]["artifact_sha256"]:
        raise ValueError("Original source artifact ZIP does not match recorded SHA-256")
    expected = {r["record_id"] for r in receipts["receipts"]}
    expected_files = (
        {f"{key}.pdf" for key in expected}
        | {f"{key}.provenance.json" for key in expected}
        | {"source-capture-summary.json"}
    )
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        names = archive.namelist()
        if len(names) != len(expected_files) or set(names) != expected_files:
            raise ValueError("Unexpected, duplicate or missing FDA capture artifact files")
        for item in archive.infolist():
            if item.is_dir() or item.file_size > 20 * 1024 * 1024:
                raise ValueError("Unsafe FDA archive entry type or size")
        confirmed = []
        for item in receipts["receipts"]:
            key = item["record_id"]
            pdf_bytes = archive.read(f"{key}.pdf")
            evidence = json.loads(archive.read(f"{key}.provenance.json"))
            if (hashlib.sha256(pdf_bytes).hexdigest() != item["pdf_sha256"]
                    or len(pdf_bytes) != item["response_byte_length"]
                    or not pdf_bytes.startswith(b"%PDF-")
                    or b"%%EOF" not in pdf_bytes[-2048:]
                    or evidence.get("sha256OfCapturedBytes") != item["pdf_sha256"]
                    or evidence.get("byteLength") != item["response_byte_length"]
                    or evidence.get("exactRequestedFdaUrl") != item["original_url"]
                    or evidence.get("modelEligible") is not False):
                raise ValueError("Captured FDA original PDF bytes/provenance mismatch")
            confirmed.append(key)
    return {
        "status": "SOURCE_BYTES_AND_CAPTURE_METADATA_HASHES_RECOMPUTED",
        "matchedPdfDocuments": len(confirmed),
        "recordIds": sorted(confirmed),
        "independentReviewCycleAdjudication": False,
        "firstPublicLetterDateVerified": False,
        "modelEligibleRecords": 0,
        "approvalProbability": None,
    }
