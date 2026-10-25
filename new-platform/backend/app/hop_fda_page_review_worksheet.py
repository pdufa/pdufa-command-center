"""Turn provisional FDA PDF page hits into a strictly quarantined reviewer worksheet.

A row is a *published letter source reference*, NOT an adjudicated FDA action.
Reviewers must consult the original document and independent historical sources.
No worksheet field can mark a review cycle, outcome or predictor as verified.
"""
from __future__ import annotations

import csv
import io
import re
from collections import Counter
from urllib.parse import urlparse

PAGES_STATUS = "FDA_SHARED_PDF_PAGE_CANDIDATES_REQUIRE_HUMAN_ADJUDICATION"
GROUPS_STATUS = "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"
SHA256 = re.compile(r"[0-9a-f]{64}")
ALLOWED_STATUS = {
    "DATE_AND_ID_PAGE_CANDIDATES",
    "ID_ONLY_PAGE_CANDIDATES",
    "NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES",
    "NO_CANONICAL_APPLICATION_FOR_PAGE_MATCH",
    "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW",
    "PDF_NO_EXTRACTABLE_TEXT",
    "PDF_TEXT_EXTRACTION_FAILED",
    "PDF_PAGE_COUNT_OUT_OF_BOUNDS",
    "PDF_BYTES_INVALID",
    "OFFICIAL_PDF_FETCH_UNAVAILABLE",
    "OFFICIAL_PDF_NOT_CONFIRMED",
    "OFFICIAL_RESPONSE_NOT_PDF",
    "PDF_EXCEEDS_DOWNLOAD_LIMIT",
    "PDF_HEADER_INVALID",
}
COLUMNS = (
    "review_priority", "review_reason", "source_record_sha256", "fda_pdf_sha256",
    "fda_pdf_url", "provisional_page_link", "published_application_ids",
    "canonical_application_candidates", "source_letter_date_as_published",
    "published_letter_type", "candidate_status", "candidate_pages_1_based",
    "candidate_page_count", "cross_application_pdf", "same_date_type_collision",
    "original_letter_page_range_verified", "effective_fda_action_date_verified",
    "regulatory_review_cycle_verified", "regulatory_outcome_verified",
    "independent_review_complete", "model_eligible", "review_status",
    "first_reviewer", "first_reviewer_observed_page_range",
    "first_reviewer_original_fda_action_date", "first_reviewer_document_action_type",
    "first_reviewer_evidence_notes", "second_reviewer",
    "second_reviewer_evidence_notes", "independent_discrepancy_resolution",
)


def _official_url(url: object) -> bool:
    if not isinstance(url, str):
        return False
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "download.open.fda.gov"
        and parsed.path.startswith("/crl/")
        and parsed.path.endswith(".pdf")
        and parsed.query == "" and parsed.fragment == ""
        and parsed.port is None and parsed.username is None and parsed.password is None
    )


def _review_priority(status: str, candidates: list, multi_app: bool, collision: bool):
    if multi_app:
        return 1, "MULTI_APPLICATION_PDF_REQUIRES_LETTER_ATTRIBUTION"
    if collision:
        return 2, "SAME_DATE_AND_TYPE_COLLISION_REQUIRES_LETTER_ATTRIBUTION"
    if status == "DATE_AND_ID_PAGE_CANDIDATES":
        if len(candidates) == 1:
            return 3, "SINGLE_STRONG_PAGE_CANDIDATE_NEEDS_INDEPENDENT_REVIEW"
        return 4, "MULTIPLE_STRONG_PAGE_CANDIDATES"
    if status == "ID_ONLY_PAGE_CANDIDATES":
        return 5, "APPLICATION_ID_ONLY_NO_SAME_PAGE_DATE"
    return 6, "NO_NARROW_PAGE_CANDIDATE_MANUAL_SOURCE_REVIEW"


def build_pdf_page_review_worksheet(pages: dict, shared: dict) -> tuple[list[dict], dict]:
    """Exact source hash/ID/date and page-count reconciliation; no outcome labels."""
    if (not isinstance(pages, dict) or pages.get("status") != PAGES_STATUS
            or not isinstance(shared, dict) or shared.get("status") != GROUPS_STATUS):
        raise ValueError("requires quarantined original FDA source and page candidates")
    page_groups = pages.get("records")
    shared_groups = shared.get("records")
    if (not isinstance(page_groups, list) or not isinstance(shared_groups, list)
            or not page_groups or len(page_groups) != len(shared_groups)):
        raise ValueError("shared-PDF source counts do not match provisional page results")
    shared_by_sha = {}
    for group in shared_groups:
        if (not isinstance(group, dict)
                or group.get("model_eligible") is not False
                or group.get("individual_letter_page_ranges_verified") is not False
                or group.get("individual_review_cycle_outcomes_verified") is not False):
            raise ValueError("shared PDF group is not quarantined")
        digest = group.get("official_fda_pdf_sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest) or digest in shared_by_sha:
            raise ValueError("missing, repeated or malformed PDF SHA256")
        shared_by_sha[digest] = group

    rows = []
    statuses = Counter()
    priorities = Counter()
    used_groups = set()
    all_source_ids = set()
    for group in page_groups:
        if (not isinstance(group, dict)
                or group.get("model_eligible") is not False
                or group.get("document_page_ranges_independently_verified") is not False
                or group.get("review_cycle_outcomes_independently_verified") is not False):
            raise ValueError("page candidate source is not quarantined")
        digest = group.get("official_fda_pdf_sha256")
        if digest not in shared_by_sha or digest in used_groups:
            raise ValueError("unknown or repeated page candidate PDF SHA")
        used_groups.add(digest)
        original = shared_by_sha[digest]
        url = original.get("official_fda_pdf_url")
        if not _official_url(url) or group.get("official_fda_pdf_url") != url:
            raise ValueError("PDF page candidate URL must exactly match official FDA source")
        letter_records = original.get("source_letter_records")
        page_records = group.get("letter_page_candidates")
        if (not isinstance(letter_records, list) or not isinstance(page_records, list)
                or len(letter_records) < 2 or len(page_records) != len(letter_records)
                or group.get("source_letter_record_count") != len(letter_records)
                or original.get("published_letter_record_count") != len(letter_records)):
            raise ValueError("letter page records do not reconcile to shared PDF")
        letters_by_hash = {}
        for source in letter_records:
            hash_ = source.get("source_record_sha256") if isinstance(source, dict) else None
            if (not isinstance(hash_, str) or not SHA256.fullmatch(hash_)
                    or hash_ in letters_by_hash or hash_ in all_source_ids):
                raise ValueError("repeated or invalid FDA source letter hash")
            letters_by_hash[hash_] = source
            all_source_ids.add(hash_)
        used_letter_ids = set()
        multi_app = original.get("multiple_application_candidates_in_one_pdf")
        collision = original.get("same_source_date_and_type_collision")
        if type(multi_app) is not bool or type(collision) is not bool:
            raise ValueError("ambiguous document-level review flags")
        for record in page_records:
            if not isinstance(record, dict):
                raise ValueError("invalid letter page result")
            source_id = record.get("source_record_sha256")
            if source_id not in letters_by_hash or source_id in used_letter_ids:
                raise ValueError("missing or repeated letter-to-PDF page candidate")
            used_letter_ids.add(source_id)
            source = letters_by_hash[source_id]
            if (record.get("application_ids_as_published") != source.get("application_ids_as_published")
                    or record.get("source_letter_date_as_published") != source.get("source_letter_date_as_published")):
                raise ValueError("original letter application IDs or dates were altered")
            if (record.get("model_eligible") is not False
                    or record.get("individual_letter_page_range_independently_verified") is not False
                    or record.get("effective_fda_action_date_independently_verified") is not False
                    or record.get("regulatory_outcome_independently_verified") is not False
                    or record.get("proposed_letter_page_range") is not None):
                raise ValueError("FDA provisional page review cannot self-certify an outcome")
            status = record.get("candidate_status")
            matches = record.get("candidate_pages")
            if status not in ALLOWED_STATUS or not isinstance(matches, list):
                raise ValueError("invalid provisional page matching status")
            max_page = group.get("page_count")
            seen_page_nums = set()
            for match in matches:
                page = match.get("page_number_1_based") if isinstance(match, dict) else None
                if (type(page) is not int or page < 1 or page in seen_page_nums
                        or type(max_page) is not int or page > max_page
                        or match.get("provisional_only") is not True
                        or match.get("application_id_token_found") is not True):
                    raise ValueError("invalid provisional PDF page reference")
                if status == "DATE_AND_ID_PAGE_CANDIDATES":
                    if (match.get("published_letter_date_token_found") is not True
                            or match.get("evidence_grade") != "SAME_PAGE_ID_AND_LETTER_DATE"):
                        raise ValueError("reported strong page match is not supported")
                if status == "ID_ONLY_PAGE_CANDIDATES":
                    if (match.get("published_letter_date_token_found") is not False
                            or match.get("evidence_grade") != "PAGE_ID_ONLY"):
                        raise ValueError("reported weak page match is not supported")
                seen_page_nums.add(page)
            if (len(matches) != record.get("candidate_page_count")
                    or status in {"DATE_AND_ID_PAGE_CANDIDATES", "ID_ONLY_PAGE_CANDIDATES"} and not matches
                    or status not in {"DATE_AND_ID_PAGE_CANDIDATES", "ID_ONLY_PAGE_CANDIDATES"} and matches):
                raise ValueError("candidate status and page counts conflict")
            priority, reason = _review_priority(status, matches, multi_app, collision)
            page_numbers = sorted(seen_page_nums)
            rows.append({
                "review_priority": priority,
                "review_reason": reason,
                "source_record_sha256": source_id,
                "fda_pdf_sha256": digest,
                "fda_pdf_url": url,
                "provisional_page_link": url + "#page=" + str(page_numbers[0]) if len(page_numbers) == 1 else "",
                "published_application_ids": "; ".join(source.get("application_ids_as_published") or []),
                "canonical_application_candidates": "; ".join(source.get("canonical_application_candidates") or []),
                "source_letter_date_as_published": source.get("source_letter_date_as_published"),
                "published_letter_type": source.get("published_letter_type"),
                "candidate_status": status,
                "candidate_pages_1_based": ", ".join(str(p) for p in page_numbers),
                "candidate_page_count": len(matches),
                "cross_application_pdf": multi_app,
                "same_date_type_collision": collision,
                "original_letter_page_range_verified": False,
                "effective_fda_action_date_verified": False,
                "regulatory_review_cycle_verified": False,
                "regulatory_outcome_verified": False,
                "independent_review_complete": False,
                "model_eligible": False,
                "review_status": "NOT_ADJUDICATED",
                "first_reviewer": "",
                "first_reviewer_observed_page_range": "",
                "first_reviewer_original_fda_action_date": "",
                "first_reviewer_document_action_type": "",
                "first_reviewer_evidence_notes": "",
                "second_reviewer": "",
                "second_reviewer_evidence_notes": "",
                "independent_discrepancy_resolution": "",
            })
            statuses[status] += 1
            priorities[priority] += 1
        if used_letter_ids != set(letters_by_hash):
            raise ValueError("some FDA shared document letters lack page review records")
    if used_groups != set(shared_by_sha):
        raise ValueError("page-candidate inventory does not cover all shared documents")
    rows.sort(key=lambda r: (r["review_priority"], r["source_letter_date_as_published"] or "",
                             r["fda_pdf_sha256"], r["source_record_sha256"]))
    audit = {
        "status": "FDA_PDF_PAGE_WORKSHEET_UNADJUDICATED",
        "shared_pdf_groups": len(shared_groups),
        "published_letter_rows": len(rows),
        "candidate_status_counts": dict(sorted(statuses.items())),
        "review_priority_counts": {str(k): priorities[k] for k in sorted(priorities)},
        "independently_verified_page_ranges": 0,
        "independently_verified_action_dates": 0,
        "independently_verified_review_cycle_outcomes": 0,
        "model_eligible_records": 0,
        "complete_application_denominator_verified": False,
        "prediction_probability": None,
        "limitations": [
            "Each row is a published-source letter reference, not a validated FDA review cycle.",
            "Page link is a provisional convenience anchor, not proof of page boundaries.",
            "No effective action date or outcome was independently adjudicated.",
        ],
    }
    return rows, audit


def worksheet_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=COLUMNS, extrasaction="raise",
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        if row.get("model_eligible") is not False or row.get("independent_review_complete") is not False:
            raise ValueError("cannot export promoted FDA review worksheet")
        writer.writerow(row)
    return output.getvalue()
