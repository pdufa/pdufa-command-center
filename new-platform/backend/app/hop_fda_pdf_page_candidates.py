"""Provisional page candidates for FDA PDFs shared by multiple letter records.

Only matching page TEXT to a published application ID and letter date is
attempted. A candidate page is not an independently verified letter boundary,
regulatory action, review cycle, outcome or training label.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import hashlib
import io
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_DOCUMENTS = 100
MAX_PDF_BYTES = 20_000_000
MAX_PAGES_PER_DOCUMENT = 180
MAX_PAGE_TEXT = 48_000
MAX_CANDIDATE_PAGES_PER_LETTER = 30
SAFE_SHA = re.compile(r"[0-9a-f]{64}")
FDA_DOC_STATUS = "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"

_MONTHS = (
    "", "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("FDA PDF download was redirected")


def _exact_fda_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return bool(
        parsed.scheme == "https"
        and parsed.hostname == "download.open.fda.gov"
        and parsed.path.startswith("/crl/")
        and parsed.path.endswith(".pdf")
        and not parsed.query and not parsed.fragment
        and parsed.port is None
        and parsed.username is None and parsed.password is None
    )


def fetch_official_pdf_bytes(url: str) -> tuple[bytes | None, str]:
    if not _exact_fda_url(url):
        raise ValueError("untrusted FDA PDF origin or path")
    opener = build_opener(_NoRedirect())
    try:
        req = Request(url, headers={
            "User-Agent": "PDUFA-HOP-source-page-review/1.0",
            "Accept": "application/pdf",
        })
        with opener.open(req, timeout=25) as response:
            if response.status != 200 or response.geturl() != url:
                return None, "OFFICIAL_PDF_NOT_CONFIRMED"
            mime = response.headers.get_content_type()
            if mime not in ("application/pdf", "application/octet-stream"):
                return None, "OFFICIAL_RESPONSE_NOT_PDF"
            data = response.read(MAX_PDF_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        return None, "OFFICIAL_PDF_FETCH_UNAVAILABLE"
    if len(data) > MAX_PDF_BYTES:
        return None, "PDF_EXCEEDS_DOWNLOAD_LIMIT"
    if not data.startswith(b"%PDF-"):
        return None, "PDF_HEADER_INVALID"
    return data, "OFFICIAL_PDF_BYTES_RETRIEVED"


def pdf_page_texts(document_bytes: bytes) -> tuple[list[str] | None, str]:
    """Extract without OCR. Scanned/complex PDFs remain manual-review cases."""
    if len(document_bytes) > MAX_PDF_BYTES or not document_bytes.startswith(b"%PDF-"):
        return None, "PDF_BYTES_INVALID"
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(document_bytes), strict=False)
        if not 1 <= len(reader.pages) <= MAX_PAGES_PER_DOCUMENT:
            return None, "PDF_PAGE_COUNT_OUT_OF_BOUNDS"
        texts = []
        for page in reader.pages:
            extracted = page.extract_text(extraction_mode="plain") or ""
            if not isinstance(extracted, str):
                extracted = ""
            texts.append(extracted[:MAX_PAGE_TEXT])
    except Exception:
        return None, "PDF_TEXT_EXTRACTION_FAILED"
    if not any(text.strip() for text in texts):
        return texts, "PDF_NO_EXTRACTABLE_TEXT"
    return texts, "PDF_TEXT_EXTRACTED"


def _letter_date_patterns(value: object) -> list[re.Pattern]:
    if not isinstance(value, str):
        return []
    try:
        parsed = datetime.strptime(value, "%m/%d/%Y")
    except ValueError:
        return []
    month = parsed.month
    day = parsed.day
    year = parsed.year
    month_name = _MONTHS[month]
    short_month = month_name[:3]
    return [
        re.compile(rf"(?<![0-9])0?{month}[/\\.-]0?{day}[/\\.-]{year}(?![0-9])", re.I),
        re.compile(rf"\\b(?:{month_name}|{short_month})\\.?\\s+0?{day},?\\s+{year}\\b", re.I),
    ]


def _application_patterns(values: object) -> list[re.Pattern]:
    if not isinstance(values, list):
        return []
    seen = set()
    patterns = []
    for value in values:
        if not isinstance(value, str):
            continue
        match = re.fullmatch(r"(NDA|ANDA|BLA)0*([0-9]{1,6})", value.upper())
        if not match:
            continue
        kind, digits = match.group(1), str(int(match.group(2)))
        key = (kind, digits)
        if key in seen:
            continue
        seen.add(key)
        patterns.append(re.compile(
            rf"(?<![A-Z0-9]){kind}\\s*[#:\\-]?\\s*0*{digits}(?![0-9])", re.I
        ))
    return patterns


def provisional_page_candidates(record: dict, page_texts: list[str]) -> dict:
    """Candidate page numbers are 1-based and MUST be independently reviewed."""
    ids = _application_patterns(record.get("canonical_application_candidates"))
    date_patterns = _letter_date_patterns(record.get("source_letter_date_as_published"))
    matches = []
    for pageno, raw in enumerate(page_texts, 1):
        text = raw[:MAX_PAGE_TEXT] if isinstance(raw, str) else ""
        matches_id = bool(ids) and any(pattern.search(text) for pattern in ids)
        matches_date = bool(date_patterns) and any(
            pattern.search(text) for pattern in date_patterns
        )
        if matches_id:
            matches.append({
                "page_number_1_based": pageno,
                "application_id_token_found": True,
                "published_letter_date_token_found": matches_date,
                "evidence_grade": "SAME_PAGE_ID_AND_LETTER_DATE" if matches_date
                                  else "PAGE_ID_ONLY",
                "provisional_only": True,
            })
    strong = [x for x in matches if x["published_letter_date_token_found"]]
    chosen = strong if strong else matches
    if len(chosen) > MAX_CANDIDATE_PAGES_PER_LETTER:
        candidates, status = [], "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW"
    elif strong:
        candidates, status = chosen, "DATE_AND_ID_PAGE_CANDIDATES"
    elif matches:
        candidates, status = chosen, "ID_ONLY_PAGE_CANDIDATES"
    elif not ids:
        candidates, status = [], "NO_CANONICAL_APPLICATION_FOR_PAGE_MATCH"
    else:
        candidates, status = [], "NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES"
    return {
        "source_record_sha256": record["source_record_sha256"],
        "application_ids_as_published": record.get("application_ids_as_published"),
        "source_letter_date_as_published": record.get("source_letter_date_as_published"),
        "candidate_status": status,
        "candidate_pages": candidates,
        "candidate_page_count": len(candidates),
        "proposed_letter_page_range": None,
        "individual_letter_page_range_independently_verified": False,
        "effective_fda_action_date_independently_verified": False,
        "regulatory_outcome_independently_verified": False,
        "model_eligible": False,
    }


def build_fda_shared_pdf_page_candidates(
    source: dict, *, fetcher=None, parser=None
) -> tuple[dict, dict]:
    if not isinstance(source, dict) or source.get("status") != FDA_DOC_STATUS:
        raise ValueError("only quarantined shared FDA PDFs can be inspected")
    groups = source.get("records")
    if not isinstance(groups, list) or not 0 < len(groups) <= MAX_DOCUMENTS:
        raise ValueError("invalid number of shared FDA PDFs")
    download = fetcher or fetch_official_pdf_bytes
    extract = parser or pdf_page_texts
    seen_digest = set()
    result = []
    statuses = Counter()
    record_statuses = Counter()
    records_total = 0
    strong_record_candidates = 0
    for group in groups:
        if (not isinstance(group, dict)
                or group.get("model_eligible") is not False
                or group.get("individual_letter_page_ranges_verified") is not False
                or group.get("individual_review_cycle_outcomes_verified") is not False):
            raise ValueError("source PDF group must remain model-ineligible")
        digest = group.get("official_fda_pdf_sha256")
        url = group.get("official_fda_pdf_url")
        records = group.get("source_letter_records")
        if (not isinstance(digest, str) or not SAFE_SHA.fullmatch(digest)
                or digest in seen_digest or not _exact_fda_url(url)
                or not isinstance(records, list) or len(records) < 2
                or group.get("published_letter_record_count") != len(records)):
            raise ValueError("invalid shared document identity or records")
        seen_digest.add(digest)
        source_ids = set()
        for rec in records:
            sha = rec.get("source_record_sha256") if isinstance(rec, dict) else None
            if (not isinstance(sha, str) or not SAFE_SHA.fullmatch(sha)
                    or sha in source_ids or rec.get("official_fda_document_url") != url):
                raise ValueError("invalid or duplicate FDA letter reference in shared PDF")
            source_ids.add(sha)
        data, status = download(url)
        if status == "OFFICIAL_PDF_BYTES_RETRIEVED":
            if not isinstance(data, bytes) or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("FDA original PDF SHA256 mismatch; archive may have changed")
            page_text, status = extract(data)
        elif data is not None:
            raise ValueError("unconfirmed FDA download cannot supply PDF bytes")
        if status == "PDF_TEXT_EXTRACTED":
            if not isinstance(page_text, list) or not all(
                    isinstance(v, str) for v in page_text):
                raise ValueError("invalid PDF page text extraction")
            letter_results = [provisional_page_candidates(rec, page_text) for rec in records]
        else:
            page_text = None
            letter_results = [
                {**provisional_page_candidates(rec, []),
                 "candidate_status": status, "candidate_pages": []}
                for rec in records
            ]
        status_counts = Counter(item["candidate_status"] for item in letter_results)
        statuses[status] += 1
        record_statuses.update(status_counts)
        records_total += len(records)
        strong_record_candidates += sum(
            item["candidate_status"] == "DATE_AND_ID_PAGE_CANDIDATES"
            for item in letter_results
        )
        result.append({
            "official_fda_pdf_sha256": digest,
            "official_fda_pdf_url": url,
            "pdf_text_extraction_status": status,
            "page_count": len(page_text) if page_text is not None else None,
            "source_letter_record_count": len(records),
            "letter_page_candidates": letter_results,
            "candidate_status_counts": dict(sorted(status_counts.items())),
            "document_page_ranges_independently_verified": False,
            "review_cycle_outcomes_independently_verified": False,
            "model_eligible": False,
        })
    audit = {
        "status": "FDA_SHARED_PDF_PAGE_CANDIDATES_REQUIRE_HUMAN_ADJUDICATION",
        "shared_pdf_groups_examined": len(result),
        "source_letter_records_examined": records_total,
        "pdf_extraction_status_counts": dict(sorted(statuses.items())),
        "letter_candidate_status_counts": dict(sorted(record_statuses.items())),
        "letters_with_same_page_id_and_letter_date_candidates": strong_record_candidates,
        "unique_documents_with_independently_verified_letter_page_ranges": 0,
        "independently_verified_effective_fda_action_dates": 0,
        "independently_verified_review_cycle_outcomes": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "Machine-extracted PDF text and candidate pages are provisional only.",
            "Shared PDF pages may include headers, footers, scanned content, corrections or multiple letters.",
            "A letter date visible on a PDF page may differ from the original effective FDA action date.",
            "No OCR or independent regulatory outcome adjudication was performed.",
        ],
    }
    return {"schema_version": 1, "status": audit["status"], "records": result}, audit
