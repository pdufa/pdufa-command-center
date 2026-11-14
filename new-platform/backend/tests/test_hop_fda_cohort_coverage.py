"""Real committed-source index reconciliation; no invented FDA outcome labels."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from app.hop_fda_cohort_coverage import (
    SOURCES, ZERO_FIELDS, DENOMINATOR_FIELDS, audit_fda_source_coverage,
    count_historical_template_rows, load_source_indexes,
)

BACKEND = Path(__file__).resolve().parents[1]
SOURCE_DIR = BACKEND / "app" / "research_sources"
HISTORICAL_TEMPLATE = BACKEND / "data" / "hop_historical_outcomes_template.csv"


def indexes():
    return load_source_indexes(SOURCE_DIR)


def test_reconciles_real_october_2026_source_indexes_without_denominator():
    data = audit_fda_source_coverage(
        indexes(), historical_template_rows=count_historical_template_rows(
            HISTORICAL_TEMPLATE
        ),
    )
    assert data["status"] == "SOURCE_COVERAGE_RECONCILED_OUTCOME_DENOMINATOR_UNKNOWN"
    assert data["source_export_dates"] == {
        "fda_published_letters": "2026-10-21",
        "approved_drug_registry": "2026-10-23",
    }
    assert data["published_letter_source_references"] == 458
    assert data["original_fda_pdf_references_byte_confirmed"] == 457
    assert data["source_references_without_released_pdf"] == 1
    assert data["unique_original_fda_pdf_documents"] == 364
    assert data["shared_pdf_documents"] == 61
    assert data["letter_references_within_shared_pdfs"] == 154
    assert data["letter_references_outside_shared_pdfs"] == 303
    assert data["additional_letter_links_over_unique_pdfs"] == 93
    assert data["identity_review_queue_references"] == 124
    assert data["published_letter_reference_to_registry_identity_links"] == {
        "APPLICATION_ID_UNRESOLVED": 15,
        "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS": 2,
        "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT": 107,
        "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT": 334,
    }
    assert data["approved_registry_application_references"] == 29416
    assert data["approved_registry_applications_by_type"] == {
        "ANDA": 23023, "BLA": 485, "NDA": 5908,
    }
    assert data["shared_document_page_review_worklist_references"] == 154
    assert data["page_candidate_status_counts"] == {
        "DATE_AND_ID_PAGE_CANDIDATES": 74,
        "ID_ONLY_PAGE_CANDIDATES": 75,
        "NO_APPLICATION_TOKEN_ON_EXTRACTED_PAGES": 3,
        "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW": 2,
    }
    assert data["page_review_priority_counts"] == {
        "1": 4, "3": 53, "4": 21, "5": 71, "6": 5,
    }
    assert data["historical_csv_unverified_claim_rows"] == 0
    assert data["fda_review_cycle_outcomes_independently_verified"] == 0
    assert data["complete_nda_bla_review_cycle_population"] is None
    assert data["complete_fda_decision_denominator_verified"] is False
    assert data["model_eligible_records"] == 0
    assert data["approval_rate"] is None
    assert data["prediction_probability"] is None
    assert data["predictive_accuracy"] is None
    assert data["readiness"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize("source_name", sorted(SOURCES))
def test_every_source_must_remain_outcome_quarantined(source_name):
    data = indexes()
    data[source_name]["model_eligible_records"] = 1
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


@pytest.mark.parametrize("source_name", sorted(SOURCES))
def test_denominator_never_self_certified_by_source_index(source_name):
    data = indexes()
    data[source_name][DENOMINATOR_FIELDS[source_name]] = True
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


@pytest.mark.parametrize("source_name", sorted(SOURCES))
def test_independent_review_claim_cannot_be_injected(source_name):
    data = indexes()
    data[source_name][ZERO_FIELDS[source_name][0]] = 1
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


@pytest.mark.parametrize("item,field,new_value", [
    ("letters", "published_letter_records", 459),
    ("pdfs", "full_official_pdf_bytes_confirmed", 456),
    ("documents", "unique_confirmed_pdf_documents", 365),
    ("documents", "letter_records_in_shared_pdf_groups", 153),
    ("crosswalk", "approved_registry_source_application_records", 29417),
    ("identity_queue", "review_queue_records", 123),
    ("registry", "source_application_records", 29415),
    ("page_candidates", "source_letter_records_examined", 153),
    ("page_worksheet", "published_letter_rows", 153),
])
def test_changed_population_counts_are_not_silently_accepted(item, field, new_value):
    data = indexes()
    data[item][field] = new_value
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


def test_source_manifest_sha_and_export_dates_must_reconcile():
    data = indexes()
    data["page_worksheet"]["source_archive_sha256"] = "e" * 64
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)
    data = indexes()
    data["page_candidates"]["source_export_date"] = "2026-10-20"
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


def test_review_worklist_candidate_distribution_not_mutually_interchangeable():
    data = indexes()
    categories = data["page_worksheet"]["candidate_status_counts"]
    categories["ID_ONLY_PAGE_CANDIDATES"] -= 1
    categories["DATE_AND_ID_PAGE_CANDIDATES"] += 1
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)


def test_missing_index_empty_headers_and_unsupported_templates_fail_closed(tmp_path):
    data = indexes()
    del data["registry"]
    with pytest.raises(ValueError):
        audit_fda_source_coverage(data, historical_template_rows=0)
    path = tmp_path / "bad.csv"
    path.write_text("case_id,application_id\n", encoding="utf-8")
    with pytest.raises(ValueError):
        count_historical_template_rows(path)
    path.write_text(HISTORICAL_TEMPLATE.read_text(encoding="utf-8")
                    + "overspecified,row\n", encoding="utf-8")
    with pytest.raises(ValueError):
        count_historical_template_rows(path)


def test_nonzero_csv_claim_rows_are_never_promoted_into_independent_decisions():
    data = audit_fda_source_coverage(indexes(), historical_template_rows=18)
    assert data["historical_csv_unverified_claim_rows"] == 18
    assert data["fda_review_cycle_outcomes_independently_verified"] == 0
    assert data["predictive_accuracy"] is None
    assert data["complete_nda_bla_review_cycle_population"] is None
