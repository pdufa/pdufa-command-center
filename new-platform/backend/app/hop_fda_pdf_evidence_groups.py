"""FDA document-evidence grouping before review-cycle adjudication.

Several published FDA letter records point to the SAME multipage FDA PDF.
Verifying the PDF bytes does not identify which pages or actions support each
record. Never turn one shared PDF into multiple verified review-cycle labels.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import re

SOURCE_ACTION_STATUS = "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES"
PDF_AUDIT_STATUS = "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION"
SHA256 = re.compile(r"[a-f0-9]{64}")


def reconcile_fda_pdf_evidence_groups(actions: dict, documents: dict) -> tuple[dict, dict]:
    if actions.get("status") != SOURCE_ACTION_STATUS or documents.get("status") != PDF_AUDIT_STATUS:
        raise ValueError("FDA source document grouping requires quarantined action and PDF audits")
    action_rows = actions.get("records")
    document_rows = documents.get("records")
    if (not isinstance(action_rows, list) or not isinstance(document_rows, list)
            or len(action_rows) != len(document_rows)):
        raise ValueError("FDA action/PDF record totals must match")
    original = {}
    for row in action_rows:
        if (not isinstance(row, dict) or row.get("model_eligible") is not False
                or row.get("effective_fda_action_date_independently_verified") is not False
                or row.get("fda_review_cycle_outcome") is not None):
            raise ValueError("unverified FDA source cannot be promoted to a regulatory outcome")
        digest = row.get("source_record_sha256")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest) or digest in original:
            raise ValueError("duplicated or invalid source record identifier")
        original[digest] = row
    seen = set()
    by_document = defaultdict(list)
    status_counts = Counter()
    missing = []
    for row in document_rows:
        if (not isinstance(row, dict) or row.get("model_eligible") is not False
                or row.get("effective_fda_action_date_verified") is not False
                or row.get("document_identity_adjudicated") is not False
                or row.get("review_cycle_verified") is not False):
            raise ValueError("FDA PDF source verification cannot be promoted to an outcome")
        source_sha = row.get("source_record_sha256")
        if source_sha not in original or source_sha in seen:
            raise ValueError("unknown or repeated FDA letter PDF reference")
        seen.add(source_sha)
        item = original[source_sha]
        if (row.get("source_application_ids_as_published") != item.get("application_ids_as_published")
                or row.get("letter_type_as_published") != item.get("letter_type_as_published")
                or row.get("letter_date_as_published") != item.get("letter_date_as_published")
                or row.get("source_file_name_as_published") != item.get("file_name_as_published")):
            raise ValueError("official PDF link does not reconcile to published FDA letter")
        status = row.get("document_fetch_status")
        if not isinstance(status, str):
            raise ValueError("missing official FDA document fetch status")
        status_counts[status] += 1
        document_sha = row.get("full_document_sha256_if_confirmed")
        url = row.get("official_fda_pdf_url_if_confirmed")
        if status == "OFFICIAL_PDF_BYTES_CONFIRMED":
            if (not isinstance(document_sha, str) or not SHA256.fullmatch(document_sha)
                    or not isinstance(url, str)
                    or not url.startswith("https://download.open.fda.gov/crl/")
                    or not url.endswith(".pdf")):
                raise ValueError("official document proof must include exact FDA URL and SHA256")
            by_document[document_sha].append({
                "source_record_sha256": source_sha,
                "source_letter_date_as_published": item.get("source_letter_date_as_published"),
                "published_letter_type": item.get("letter_type_as_published"),
                "application_ids_as_published": item.get("application_ids_as_published"),
                "canonical_application_candidates": item.get("canonical_application_candidates"),
                "official_fda_document_url": url,
            })
        else:
            if document_sha is not None or url is not None:
                raise ValueError("unconfirmed FDA PDF cannot carry a verified URL or fingerprint")
            missing.append(source_sha)
    if seen != set(original):
        raise ValueError("FDA document source check does not cover all published letters")

    work = []
    additional_links = 0
    shared_rows = 0
    multi_application_groups = 0
    same_date_type_collision_groups = 0
    shared_groups = 0
    for document_sha, rows in by_document.items():
        if len(rows) <= 1:
            continue
        shared_groups += 1
        shared_rows += len(rows)
        additional_links += len(rows) - 1
        urls = {r["official_fda_document_url"] for r in rows}
        if len(urls) != 1:
            raise ValueError("one FDA PDF fingerprint has multiple incompatible source URLs")
        app_candidates = {tuple(r["canonical_application_candidates"] or []) for r in rows}
        different_applications = len(app_candidates) > 1
        if different_applications:
            multi_application_groups += 1
        day_type = [(r["source_letter_date_as_published"], r["published_letter_type"]) for r in rows]
        same_date_collision = len(set(day_type)) != len(day_type)
        if same_date_collision:
            same_date_type_collision_groups += 1
        work.append({
            "official_fda_pdf_sha256": document_sha,
            "official_fda_pdf_url": rows[0]["official_fda_document_url"],
            "published_letter_record_count": len(rows),
            "source_letter_records": sorted(rows, key=lambda x: (
                x["source_letter_date_as_published"] or "", x["source_record_sha256"]
            )),
            "multiple_application_candidates_in_one_pdf": different_applications,
            "same_source_date_and_type_collision": same_date_collision,
            "individual_letter_page_ranges_verified": False,
            "fda_effective_action_dates_verified": False,
            "individual_review_cycle_outcomes_verified": False,
            "individual_letter_page_ranges": None,
            "independent_review_complete": False,
            "model_eligible": False,
            "review_status": "NEEDS_DOCUMENT_PAGE_LEVEL_MAPPING",
        })
    work.sort(key=lambda x: (
        -int(x["multiple_application_candidates_in_one_pdf"]),
        -int(x["same_source_date_and_type_collision"]),
        -x["published_letter_record_count"], x["official_fda_pdf_sha256"],
    ))
    official_links = sum(status_counts.values()) - len(missing)
    if official_links != sum(len(v) for v in by_document.values()):
        raise ValueError("FDA confirmed-document counts do not reconcile")
    audit = {
        "status": "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION",
        "published_letter_source_records": len(action_rows),
        "official_pdf_confirmed_letter_references": official_links,
        "unique_confirmed_pdf_documents": len(by_document),
        "distinct_shared_pdf_groups": shared_groups,
        "letter_records_in_shared_pdf_groups": shared_rows,
        "additional_letter_links_beyond_unique_pdfs": additional_links,
        "shared_documents_containing_multiple_applications": multi_application_groups,
        "same_date_and_letter_type_collision_groups": same_date_type_collision_groups,
        "source_records_without_confirmed_pdf": len(missing),
        "source_records_without_confirmed_pdf_sha256": sorted(missing),
        "individual_letter_page_ranges_verified": 0,
        "independently_verified_fda_action_dates": 0,
        "independently_verified_review_cycle_outcomes": 0,
        "complete_application_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "limitations": [
            "A single FDA PDF may bundle separate letters from different years or applications.",
            "PDF fingerprints verify bytes; they cannot locate the correct page or letter without page-level review.",
            "Shared documents cannot be counted as one outcome, nor as independently verified multiple outcomes.",
            "Published CRLs are not a complete review-cycle denominator.",
        ],
    }
    if (audit["unique_confirmed_pdf_documents"]
            + audit["additional_letter_links_beyond_unique_pdfs"]
            + audit["source_records_without_confirmed_pdf"] != len(action_rows)):
        raise ValueError("FDA unique-document denominator does not reconcile to letter records")
    return {"schema_version": 1, "status": audit["status"], "records": work}, audit
