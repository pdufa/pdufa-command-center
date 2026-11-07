"""Cross-index FDA source coverage and missing-denominator diagnostic.

Uses committed, quarantine-only FDA source summaries; verifies their mutual
consistency, but does not download/read PDFs or adjudicate review-cycle outcomes.
Source/letter/application counts are NEVER interpreted as clinical approval rates.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from .hop_outcomes_import import REQUIRED_COLUMNS

SOURCES = {
    "letters": "hop_openfda_crl_audit_index.json",
    "pdfs": "hop_fda_full_action_pdf_audit_index.json",
    "documents": "hop_fda_shared_pdf_reconciliation_index.json",
    "crosswalk": "hop_fda_crosswalk_audit_index.json",
    "identity_queue": "hop_fda_identity_review_queue_index.json",
    "registry": "hop_drugsfda_audit_index.json",
    "page_candidates": "hop_fda_shared_pdf_page_candidate_index.json",
    "page_worksheet": "hop_fda_page_review_worksheet_audit_index.json",
}
STATUSES = {
    "letters": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
    "pdfs": "ALL_PUBLISHED_FDA_ACTION_PDFS_QUARANTINED_NOT_VALIDATED_OUTCOMES",
    "documents": "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION",
    "crosswalk": "QUARANTINED_IDENTITY_LINKAGE_ONLY_NOT_OUTCOME_COHORT",
    "identity_queue": "IDENTITY_REVIEW_QUEUE_NOT_OUTCOME_COHORT",
    "registry": "QUARANTINED_APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
    "page_candidates": "FDA_SHARED_PDF_PAGE_CANDIDATES_REQUIRE_HUMAN_ADJUDICATION",
    "page_worksheet": "FDA_PDF_PAGE_WORKSHEET_UNADJUDICATED",
}
ZERO_FIELDS = {
    "letters": ("verified_application_review_cycles", "model_eligible_records"),
    "pdfs": (
        "effective_fda_action_dates_independently_verified",
        "adjudicated_review_cycle_outcomes", "model_eligible_records",
    ),
    "documents": (
        "individual_letter_page_ranges_verified",
        "independently_verified_fda_action_dates",
        "independently_verified_review_cycle_outcomes", "model_eligible_records",
    ),
    "crosswalk": ("verified_review_cycle_outcomes", "model_eligible_records"),
    "identity_queue": ("independently_verified_review_cycles", "model_eligible_records"),
    "registry": (
        "independently_verified_review_cycle_outcomes", "model_eligible_records",
    ),
    "page_candidates": (
        "uniquely_independently_verified_letter_page_ranges",
        "effective_fda_action_dates_independently_verified",
        "independently_verified_review_cycle_outcomes", "model_eligible_records",
    ),
    "page_worksheet": (
        "independently_verified_page_ranges",
        "independently_verified_action_dates",
        "independently_verified_review_cycle_outcomes", "model_eligible_records",
    ),
}
DENOMINATOR_FIELDS = {
    "letters": "verified_complete_application_denominator",
    "pdfs": "complete_application_denominator_verified",
    "documents": "complete_application_denominator_verified",
    "crosswalk": "complete_application_denominator_verified",
    "identity_queue": "complete_application_denominator_verified",
    "registry": "complete_application_denominator_verified",
    "page_candidates": "complete_application_denominator_verified",
    "page_worksheet": "complete_application_denominator_verified",
}
REASON_CODES = (
    "COMPLETE_FDA_NDA_BLA_REVIEW_CYCLE_DENOMINATOR_NOT_RECONSTRUCTED",
    "PUBLISHED_CRL_COLLECTION_NOT_UNBIASED_DECISION_POPULATION",
    "DRUGSFDA_APPROVAL_CENTRIC_REGISTRY_NOT_NONAPPROVAL_DENOMINATOR",
    "ORIGINAL_FDA_ACTION_DATE_AND_CYCLE_NOT_INDEPENDENTLY_ADJUDICATED",
    "MULTIPLE_LETTERS_MAY_MAP_TO_ONE_REVIEW_CYCLE",
    "MISSING_OR_UNRELEASED_SOURCE_PDFS",
    "INDEPENDENT_REVIEWER_SIGNOFF_AND_PREDECISION_FEATURES_MISSING",
    "CHRONOLOGICAL_MODEL_CALIBRATION_NOT_PERFORMED",
)


def _integer(record: dict, key: str) -> int:
    value = record.get(key)
    if type(value) is not int or value < 0:
        raise ValueError("Missing or negative source count: " + key)
    return value


def _counts(record: dict, key: str) -> dict[str, int]:
    result = record.get(key)
    if (not isinstance(result, dict) or not result
            or any(not isinstance(k, str) or not k or type(v) is not int or v < 0
                   for k, v in result.items())):
        raise ValueError("Invalid published source category counts: " + key)
    return result


def _same(value: int, *others: int) -> None:
    if any(other != value for other in others):
        raise ValueError("FDA source indices contain conflicting counts")


def load_source_indexes(directory: str | Path) -> dict[str, dict]:
    result = {}
    for key, filename in SOURCES.items():
        with (Path(directory) / filename).open(encoding="utf-8") as stream:
            result[key] = json.load(stream)
    return result


def count_historical_template_rows(path: str | Path) -> int:
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(REQUIRED_COLUMNS):
            raise ValueError("Historical FDA intake has missing, extra or reordered columns")
        # Reject malformed/extra cells and duplicate headers; report count only,
        # not scientific validity or the number of adjudicated decisions.
        count = 0
        for item in reader:
            if None in item or any(v is None for v in item.values()):
                raise ValueError("Malformed historical FDA CSV row")
            count += 1
    return count


def audit_fda_source_coverage(indexes: dict[str, dict], *,
                              historical_template_rows: int) -> dict:
    if not isinstance(indexes, dict) or set(indexes) != set(SOURCES):
        raise ValueError("Missing/extra committed FDA source index")
    if type(historical_template_rows) is not int or historical_template_rows < 0:
        raise ValueError("Invalid historical CSV claim row count")
    for name, status in STATUSES.items():
        item = indexes[name]
        if (not isinstance(item, dict) or item.get("schema_version") != 1
                or item.get("status") != status
                or item.get("prediction_probability") is not None
                or item.get(DENOMINATOR_FIELDS[name]) is not False
                or any(_integer(item, field) != 0 for field in ZERO_FIELDS[name])):
            raise ValueError("Source index may not claim FDA adjudication or model clearance")

    letters, pdfs, docs = (indexes[n] for n in ("letters", "pdfs", "documents"))
    cross, queue = (indexes[n] for n in ("crosswalk", "identity_queue"))
    reg, pages, worksheet = (indexes[n] for n in
                             ("registry", "page_candidates", "page_worksheet"))

    n = _integer(letters, "published_letter_records")
    _same(n, _integer(letters, "quarantined_letter_records"),
          _integer(pdfs, "published_letter_records"),
          _integer(docs, "published_letter_source_records"),
          _integer(cross, "published_letter_records"),
          _integer(queue, "published_letter_records"))
    if n == 0:
        raise ValueError("Source audit has no published letter references")

    pdf_count = _integer(pdfs, "full_official_pdf_bytes_confirmed")
    missing = _integer(pdfs, "source_records_without_safe_pdf_filename")
    distinct_pdf = _integer(docs, "unique_confirmed_pdf_documents")
    shared_pdf = _integer(docs, "distinct_shared_pdf_groups")
    shared_refs = _integer(docs, "letter_records_in_shared_pdf_groups")
    additional_links = _integer(docs, "additional_letter_links_beyond_unique_pdfs")
    _same(pdf_count + missing, n)
    _same(pdf_count, _integer(docs, "official_pdf_confirmed_letter_references"))
    _same(missing, _integer(docs, "source_records_without_confirmed_pdf"))
    _same(pdf_count - distinct_pdf, additional_links, shared_refs - shared_pdf)
    if (not (0 <= shared_pdf <= distinct_pdf <= pdf_count <= n)
            or shared_refs < shared_pdf or shared_refs > pdf_count):
        raise ValueError("Impossible source-PDF-to-letter relationship")

    source_hashes = (
        pdfs.get("original_fda_archive_sha256"),
        docs.get("original_fda_archive_sha256"),
        pages.get("source_archive_sha256"),
        worksheet.get("source_archive_sha256"),
    )
    if (any(not isinstance(v, str) or len(v) != 64
            or any(c not in "0123456789abcdef" for c in v)
            for v in source_hashes)
            or len(set(source_hashes)) != 1):
        raise ValueError("Source audit snapshots do not share original archive digest")

    identity_counts = _counts(cross, "identity_link_status_counts")
    expected_identity_keys = {
        "APPLICATION_ID_UNRESOLVED",
        "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS",
        "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
        "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT",
    }
    if set(identity_counts) != expected_identity_keys or sum(identity_counts.values()) != n:
        raise ValueError("Unreconciled published letter/approved registry identity crosswalk")
    queued_identity = (
        identity_counts["APPLICATION_ID_UNRESOLVED"]
        + identity_counts["MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"]
        + identity_counts["NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"]
    )
    queue_counts = _counts(queue, "review_reason_counts")
    for key in expected_identity_keys - {"PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"}:
        _same(identity_counts[key], queue_counts.get(key, -1))
    _same(queued_identity, _integer(queue, "review_queue_records"))
    _same(n - queued_identity, _integer(queue, "already_identity_linked_records"))
    _same(queued_identity + (n - queued_identity), n)

    registry_apps = _integer(reg, "source_application_records")
    registry_by_type = _counts(reg, "application_number_prefixes")
    if (set(registry_by_type) != {"NDA", "BLA", "ANDA"}
            or sum(registry_by_type.values()) != registry_apps
            or registry_apps == 0
            or registry_apps != _integer(cross, "approved_registry_source_application_records")):
        raise ValueError("Registry extraction/identity index does not reconcile")

    _same(shared_pdf,
          _integer(pages, "shared_pdf_groups_examined"),
          _integer(worksheet, "shared_pdf_groups"))
    _same(shared_refs,
          _integer(pages, "source_letter_records_examined"),
          _integer(worksheet, "published_letter_rows"))
    if (pages.get("status") != STATUSES["page_candidates"]
            or pages.get("pdf_text_extraction_status_counts") !=
            {"PDF_TEXT_EXTRACTED": shared_pdf}):
        raise ValueError("Published PDF page-extraction status not coherent")
    candidate_counts = _counts(pages, "letter_candidate_status_counts")
    if (candidate_counts != _counts(worksheet, "candidate_status_counts")
            or sum(candidate_counts.values()) != shared_refs
            or set(candidate_counts) != {
                "DATE_AND_ID_PAGE_CANDIDATES",
                "ID_ONLY_PAGE_CANDIDATES",
                "NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES",
                "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW",
            }):
        raise ValueError("Page evidence candidate categories do not reconcile")
    priorities = _counts(worksheet, "review_priority_counts")
    # Priority-1 entries in this frozen worksheet are the four ID-only
    # multi-application references. Priority-6 covers the five records with
    # no narrowed page match. These are SOURCE REFERENCES, not FDA cycles.
    if (sum(priorities.values()) != shared_refs
            or set(priorities) != {"1", "3", "4", "5", "6"}
            or priorities["3"] != _integer(pages, "letter_date_id_one_candidate_page_records")
            or priorities["4"] != _integer(pages, "letter_date_id_multiple_candidate_pages_records")
            or priorities["3"] + priorities["4"] !=
               candidate_counts["DATE_AND_ID_PAGE_CANDIDATES"]
            or priorities["1"] + priorities["5"] !=
               candidate_counts["ID_ONLY_PAGE_CANDIDATES"]
            or _integer(pages, "id_only_multiple_candidate_pages_records") !=
               candidate_counts["ID_ONLY_PAGE_CANDIDATES"]
            or priorities["6"] != (
               candidate_counts["NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES"]
               + candidate_counts["TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW"])):
        raise ValueError("FDA page candidate / priority review distributions mismatch")

    if (letters.get("source_export_date") != pdfs.get("official_fda_crl_export_date")
            or letters.get("source_export_date") != docs.get("fda_crl_source_export_date")
            or letters.get("source_export_date") != pages.get("source_export_date")
            or letters.get("source_export_date") != worksheet.get("source_export_date")
            or reg.get("source_export_date") != cross.get("approved_registry_source_export_date")):
        raise ValueError("FDA source export snapshots have mismatched date labels")

    return {
        "status": "SOURCE_COVERAGE_RECONCILED_OUTCOME_DENOMINATOR_UNKNOWN",
        "source_export_dates": {
            "fda_published_letters": letters["source_export_date"],
            "approved_drug_registry": reg["source_export_date"],
        },
        "published_letter_source_references": n,
        "original_fda_pdf_references_byte_confirmed": pdf_count,
        "source_references_without_released_pdf": missing,
        "unique_original_fda_pdf_documents": distinct_pdf,
        "shared_pdf_documents": shared_pdf,
        "letter_references_within_shared_pdfs": shared_refs,
        "letter_references_outside_shared_pdfs": pdf_count - shared_refs,
        "additional_letter_links_over_unique_pdfs": additional_links,
        "published_letter_reference_to_registry_identity_links": identity_counts,
        "identity_review_queue_references": queued_identity,
        "approved_registry_application_references": registry_apps,
        "approved_registry_applications_by_type": dict(sorted(registry_by_type.items())),
        "shared_document_page_review_worklist_references": shared_refs,
        "page_candidate_status_counts": dict(sorted(candidate_counts.items())),
        "page_review_priority_counts": dict(sorted(priorities.items())),
        "historical_csv_unverified_claim_rows": historical_template_rows,
        "fda_original_action_dates_independently_verified": 0,
        "fda_review_cycle_outcomes_independently_verified": 0,
        "complete_nda_bla_review_cycle_population": None,
        "complete_fda_decision_denominator_verified": False,
        "reviewer_identity_and_independent_signoff_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "unmet_gates": list(REASON_CODES),
        "unit_disclaimer": (
            "Source letter references, PDF documents and approval-centric "
            "registry applications are different units. These counts are not "
            "a complete historical cohort of original FDA NDA/BLA review cycles."
        ),
    }
