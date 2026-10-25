"""Bounded, read-only check of actual FDA CRL PDFs for identity-review cases.

A successful check verifies the official host served PDF bytes matching the
published file name. It DOES NOT verify review-cycle identity or the effective
FDA action date. Corrected letters may retain an earlier action date.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

FDA_PDF_PREFIX = "https://download.open.fda.gov/crl/"
MAX_PDF_BYTES = 20_000_000
MAX_BATCH = 25
ALLOWED_SOURCE_QUEUE_STATUSES = {
    "IDENTITY_REVIEW_QUEUE_NOT_OUTCOME_COHORT",
    "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES",
}

class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("FDA document redirected; source requires manual review")


def official_document_candidate(filename: object) -> str | None:
    """Produce a probe candidate only; do not present it as a working source."""
    if (not isinstance(filename, str) or not 5 <= len(filename) <= 160
            or ".." in filename or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_,.-]*(?: [A-Za-z0-9][A-Za-z0-9_,.-]*)*[.]pdf", filename,
                flags=re.IGNORECASE)):
        return None
    # Only encode an explicitly published, validated filename; do not infer
    # a document path or silently remove spaces from its official name.
    return FDA_PDF_PREFIX + quote(filename, safe="")


def fetch_official_pdf(url: str) -> tuple[str, str | None]:
    """Return status and full-document SHA256 only for a valid official PDF."""
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname != "download.open.fda.gov"
            or not parsed.path.startswith("/crl/") or parsed.query or parsed.fragment
            or parsed.username or parsed.password or parsed.port is not None):
        raise ValueError("not the exact official FDA document host")
    opener = build_opener(_RejectRedirect())
    req = Request(url, headers={"User-Agent": "PDUFA-HOP-public-source-audit/1.0",
                                "Accept": "application/pdf"})
    try:
        with opener.open(req, timeout=20) as response:
            if response.status != 200 or response.geturl() != url:
                return "HTTP_NOT_CONFIRMED", None
            kind = response.headers.get_content_type()
            if kind not in ("application/pdf", "application/octet-stream"):
                return "NOT_A_PDF_RESPONSE", None
            content = response.read(MAX_PDF_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return "FETCH_NOT_CONFIRMED", None
    if len(content) > MAX_PDF_BYTES:
        return "PDF_EXCEEDS_SAFE_SIZE_LIMIT", None
    if not content.startswith(b"%PDF-"):
        return "PDF_HEADER_INVALID", None
    return "OFFICIAL_PDF_BYTES_CONFIRMED", hashlib.sha256(content).hexdigest()


def probe_fda_review_documents(queue: dict, *, offset: int = 0,
                               limit: int = 20, fetcher=None) -> tuple[dict, dict]:
    if queue.get("status") not in ALLOWED_SOURCE_QUEUE_STATUSES:
        raise ValueError("not a quarantined FDA source review queue")
    records = queue.get("records")
    if not isinstance(records, list):
        raise ValueError("missing FDA identity review queue records")
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= MAX_BATCH:
        raise ValueError("invalid bounded FDA document probe parameters")
    check = fetcher or fetch_official_pdf
    out = []
    counts = Counter()
    for i, row in enumerate(records):
        if (not isinstance(row, dict) or row.get("model_eligible") is not False
                or row.get("identity_verified") is not False
                or row.get("review_cycle_verified") is not False
                or row.get("complete_denominator_verified") is not False):
            raise ValueError("source queue must remain unverified and model-ineligible")
        if queue["status"] == "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES" and (
                row.get("effective_fda_action_date_independently_verified") is not False
                or row.get("fda_review_cycle_outcome") is not None
                or row.get("review_cycle_number_verified") is not False
                or row.get("independent_review_complete") is not False):
            raise ValueError("published FDA action review cannot self-certify outcomes")
        digest = row.get("source_record_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
            raise ValueError("invalid source-record SHA256")
        status, pdf_sha, official_url = "NOT_CHECKED", None, None
        if offset <= i < offset + limit:
            candidate = official_document_candidate(row.get("file_name_as_published"))
            if candidate is None:
                status = "NO_SAFE_FILENAME_TO_CHECK"
            else:
                status, pdf_sha = check(candidate)
                if status not in {
                    "OFFICIAL_PDF_BYTES_CONFIRMED", "FETCH_NOT_CONFIRMED",
                    "HTTP_NOT_CONFIRMED", "NOT_A_PDF_RESPONSE",
                    "PDF_EXCEEDS_SAFE_SIZE_LIMIT", "PDF_HEADER_INVALID"
                }:
                    raise ValueError("unexpected FDA document verification result")
                if status == "OFFICIAL_PDF_BYTES_CONFIRMED":
                    if not isinstance(pdf_sha, str) or not re.fullmatch(r"[a-f0-9]{64}", pdf_sha):
                        raise ValueError("invalid PDF evidence SHA256")
                    official_url = candidate
                elif pdf_sha is not None:
                    raise ValueError("unconfirmed documents cannot have verified digests")
        counts[status] += 1
        out.append({
            "source_record_sha256": digest,
            "source_application_ids_as_published": row.get("application_ids_as_published"),
            "source_file_name_as_published": row.get("file_name_as_published"),
            "letter_type_as_published": row.get("letter_type_as_published"),
            "letter_date_as_published": row.get("letter_date_as_published"),
            "identity_link_status": row.get("identity_link_status"),
            "document_fetch_status": status,
            "official_fda_pdf_url_if_confirmed": official_url,
            "full_document_sha256_if_confirmed": pdf_sha,
            "document_identity_adjudicated": False,
            "effective_fda_action_date_verified": False,
            "review_cycle_verified": False,
            "model_eligible": False,
        })
    audited = {
        "status": "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION",
        "total_identity_review_cases": len(records),
        "batch_offset": offset,
        "batch_limit": limit,
        "document_fetch_status_counts": dict(sorted(counts.items())),
        "official_pdf_bytes_confirmed": counts["OFFICIAL_PDF_BYTES_CONFIRMED"],
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "HTTP/PDF checks do not adjudicate application identities, original action dates or outcomes.",
            "Corrections may be published after the effective regulatory decision date.",
            "Unprobed items remain NOT_CHECKED and are not reported as inaccessible.",
            "Only published FDA CRLs are sampled; selection bias prevents probability inference.",
        ],
    }
    return {"schema_version": 1, "status": audited["status"], "records": out}, audited


def probe_all_fda_review_documents(queue: dict, *, batch_size: int = 20,
                                   fetcher=None) -> tuple[dict, dict]:
    """Check each quarantined queue record once, in bounded sequential batches.

    All HTTP/PDF checks are preliminary provenance, NOT decision adjudication.
    Nonresponsive or invalid files remain explicitly unverified.
    """
    if type(batch_size) is not int or not 1 <= batch_size <= MAX_BATCH:
        raise ValueError("invalid FDA PDF batch size")
    if queue.get("status") not in ALLOWED_SOURCE_QUEUE_STATUSES:
        raise ValueError("not an allowed quarantined FDA source queue")
    rows = queue.get("records")
    if not isinstance(rows, list):
        raise ValueError("FDA identity-review queue records missing")
    all_records = []
    totals = Counter()
    for offset in range(0, len(rows), batch_size):
        batch, audit = probe_fda_review_documents(
            queue, offset=offset, limit=batch_size, fetcher=fetcher,
        )
        for checked in batch["records"][offset:offset + batch_size]:
            if checked["document_fetch_status"] == "NOT_CHECKED":
                raise ValueError("FDA evidence probe skipped an in-range record")
            all_records.append(checked)
            totals[checked["document_fetch_status"]] += 1
    if len(all_records) != len(rows) or sum(totals.values()) != len(rows):
        raise ValueError("not every FDA identity review record was checked")
    verified = totals["OFFICIAL_PDF_BYTES_CONFIRMED"]
    audit = {
        "status": "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION",
        "total_identity_review_cases": len(rows),
        "document_fetch_status_counts": dict(sorted(totals.items())),
        "official_pdf_bytes_confirmed": verified,
        "all_cases_checked_for_document_availability": True,
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Availability check does not determine letter authenticity, identity or effective regulatory action date.",
            "PDFs can be corrections published after an earlier FDA action.",
            "An inaccessible PDF is not evidence of FDA approval or permanent rejection.",
            "Only publication-selected FDA source records were checked; the full denominator is unknown.",
        ],
    }
    return {"schema_version": 1, "status": audit["status"], "records": all_records}, audit
