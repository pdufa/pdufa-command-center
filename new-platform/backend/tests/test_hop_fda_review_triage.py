"""All queue tests are synthetic; they do not establish actual FDA outcomes."""
from __future__ import annotations

import csv
from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_page_review_worksheet import COLUMNS
from app.hop_fda_dual_review_packets import build_dual_review_packets
from app.hop_fda_reviewer_reconciliation import reconcile_review_claims
from app.hop_fda_review_triage import (
    TRIAGE_FIELDS, audit_worksheet_inventory, build_review_triage,
    review_triage_csv,
)

AS_OF = date(2026, 10, 25)


def row(source="a", priority=3, status="DATE_AND_ID_PAGE_CANDIDATES"):
    result = {key: "" for key in COLUMNS}
    result.update({
        "review_priority": str(priority),
        "review_reason": "SYNTHETIC_SOURCE_REVIEW_ONLY",
        "source_record_sha256": source * 64,
        "fda_pdf_sha256": "b" * 64,
        "fda_pdf_url": "https://download.open.fda.gov/crl/fictional.pdf",
        "provisional_page_link": "https://download.open.fda.gov/crl/fictional.pdf#page=2",
        "published_application_ids": "NDA000001",
        "canonical_application_candidates": "NDA000001",
        "source_letter_date_as_published": "2020-01-01",
        "published_letter_type": "COMPLETE RESPONSE",
        "candidate_status": status,
        "candidate_pages_1_based": "2",
        "candidate_page_count": "1",
        "cross_application_pdf": "False",
        "same_date_type_collision": "False",
        "original_letter_page_range_verified": "False",
        "effective_fda_action_date_verified": "False",
        "regulatory_review_cycle_verified": "False",
        "regulatory_outcome_verified": "False",
        "independent_review_complete": "False",
        "model_eligible": "False",
        "review_status": "NOT_ADJUDICATED",
    })
    return result


def example():
    return [
        row("a", 3),
        row("c", 5, "ID_ONLY_PAGE_CANDIDATES"),
        row("d", 1),
    ]


def pinned_index():
    return {
        "schema_version": 1,
        "status": "FDA_PDF_PAGE_WORKSHEET_UNADJUDICATED",
        "all_reviewer_fields_initially_blank": True,
        "source_record_reconciled": True,
        "complete_application_denominator_verified": False,
        "prediction_probability": None,
        "independently_verified_page_ranges": 0,
        "independently_verified_action_dates": 0,
        "independently_verified_review_cycle_outcomes": 0,
        "model_eligible_records": 0,
        "review_priority_counts": {"1": 1, "3": 1, "5": 1},
        "candidate_status_counts": {
            "DATE_AND_ID_PAGE_CANDIDATES": 2,
            "ID_ONLY_PAGE_CANDIDATES": 1,
        },
        "published_letter_rows": 3,
        "shared_pdf_groups": 1,
        "source_archive_sha256": "e" * 64,
    }


def complete(record, token):
    record.update({
        "reviewer_id": token,
        "observed_pdf_sha256": record["fda_pdf_sha256"],
        "observed_letter_pages": "2-3",
        "observed_application_ids": "NDA000001",
        "observed_action_date": "2020-01-01",
        "observed_document_type": "COMPLETE RESPONSE",
        "observed_review_cycle": "1",
        "source_evidence_notes": "Synthetic source note, not real evidence.",
    })


def prepare():
    original = example()
    first, second, _ = build_dual_review_packets(original)
    return original, first, second


def compare(original, first, second):
    return reconcile_review_claims(original, first, second, as_of=AS_OF)


def test_pinned_source_inventory_is_stable_in_any_row_order():
    original = example()
    audit = audit_worksheet_inventory(original, pinned_index())
    reversed_audit = audit_worksheet_inventory(list(reversed(original)), pinned_index())
    assert audit["source_reference_rows"] == 3
    assert audit["shared_pdf_groups"] == 1
    assert audit["status"] == "INDEX_COUNTS_RECONCILED_NO_SOURCE_ADJUDICATION"
    assert audit["worksheet_source_fingerprint_sha256"] == reversed_audit[
        "worksheet_source_fingerprint_sha256"
    ]
    assert len(audit["worksheet_source_fingerprint_sha256"]) == 64


def test_queue_sorts_conflicts_missing_reviews_and_unverified_agreement():
    original, first, second = prepare()
    for record in first:
        complete(record, "reviewer_a")
    for record in second:
        complete(record, "reviewer_b")
    # Different synthetic source states: first (a) conflicts,
    # second (c) missing, third (d) agrees but is NOT independently verified.
    second[0]["observed_review_cycle"] = "2"
    second[1]["source_evidence_notes"] = ""
    comparison = compare(original, first, second)
    queue, audit = build_review_triage(
        original, first, second, comparison, pinned_index(), as_of=AS_OF
    )
    assert [row["triage_status"] for row in queue] == [
        "REVIEWER_FINDINGS_CONFLICT",
        "REVIEW_SUBMISSIONS_INCOMPLETE",
        "MATCHING_TEXT_STILL_UNVERIFIED",
    ]
    assert [row["source_record_sha256"] for row in queue] == [
        "a" * 64, "c" * 64, "d" * 64
    ]
    assert queue[0]["disputed_fields"] == "observed_review_cycle"
    assert queue[1]["claimed_second_review_complete"] == "false"
    assert queue[2]["claimed_first_review_complete"] == "true"
    assert audit["status"] == "UNVERIFIED_REVIEW_QUEUE_ONLY"
    assert audit["queue_status_counts"] == {
        "SOURCE_METADATA_DISCREPANCY": 1,
        "REVIEWER_FINDINGS_CONFLICT": 0,
        "REVIEW_SUBMISSIONS_INCOMPLETE": 1,
        "MATCHING_TEXT_STILL_UNVERIFIED": 1,
    }
    assert audit["reviewer_identity_authenticated"] is False
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    assert audit["human_adjudication_required"] is True
    contents = review_triage_csv(queue)
    parsed = list(csv.DictReader(contents.splitlines()))
    assert len(parsed) == 3
    assert tuple(parsed[0]) == TRIAGE_FIELDS
    assert "reviewer_a" not in contents
    assert "reviewer_b" not in contents
    assert "Synthetic source note" not in contents


@pytest.mark.parametrize("change", [
    "wrong_total", "wrong_priority", "wrong_category", "wrong_pdf_groups",
    "model_promoted", "denominator_promoted", "source_hash_mutated",
    "missing_row", "duplicate_row", "archive_digest_corrupt",
])
def test_bad_pinned_index_or_modified_sources_are_blocked(change):
    rows = example()
    index = pinned_index()
    if change == "wrong_total":
        index["published_letter_rows"] = 4
    elif change == "wrong_priority":
        index["review_priority_counts"] = {"3": 2, "5": 1}
    elif change == "wrong_category":
        index["candidate_status_counts"] = {"ID_ONLY_PAGE_CANDIDATES": 3}
    elif change == "wrong_pdf_groups":
        index["shared_pdf_groups"] = 2
    elif change == "model_promoted":
        index["model_eligible_records"] = 1
    elif change == "denominator_promoted":
        index["complete_application_denominator_verified"] = True
    elif change == "source_hash_mutated":
        rows[0]["source_record_sha256"] = "invalid-digest"
    elif change == "missing_row":
        rows.pop()
    elif change == "duplicate_row":
        rows[1] = deepcopy(rows[0])
    elif change == "archive_digest_corrupt":
        index["source_archive_sha256"] = "NOT_A_HASH"
    with pytest.raises(ValueError):
        audit_worksheet_inventory(rows, index)


def test_forged_comparison_counts_cannot_create_false_consensus():
    original, first, second = prepare()
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    real = compare(original, first, second)
    forged = dict(real, matching_unverified_claims=99)
    with pytest.raises(ValueError):
        build_review_triage(
            original, first, second, forged, pinned_index(), as_of=AS_OF
        )


def test_unchanged_blank_packets_result_in_review_queue_not_outcomes():
    original, first, second = prepare()
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    assert len(queue) == 3
    assert all(item["triage_status"] == "REVIEW_SUBMISSIONS_INCOMPLETE"
               for item in queue)
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["prediction_probability"] is None


def test_two_matching_reviewers_wrong_fda_date_are_priority_one_and_unverified():
    original, first, second = prepare()
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    first[0]["observed_action_date"] = "2020-01-02"
    second[0]["observed_action_date"] = "2020-01-02"
    assert compare(original, first, second)["disagreeing_unverified_claims"] == 0
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    item = queue[0]
    assert item["source_record_sha256"] == "a" * 64
    assert item["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert item["review_queue_priority"] == "1"
    assert item["source_metadata_warning_flags"] == (
        "ACTION_DATE_DIFFERS_FROM_PUBLISHED_LETTER_DATE"
    )
    assert audit["source_metadata_warning_references"] == 1
    assert audit["independent_source_metadata_verified"] is False
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None


@pytest.mark.parametrize("field,wrong_value,expected_flag", [
    ("observed_application_ids", "BLA000009",
     "REVIEWED_APPLICATION_NOT_IN_SOURCE_CANDIDATES"),
    ("observed_document_type", "APPROVAL",
     "DOCUMENT_TYPE_DIFFERS_FROM_PUBLISHED_LETTER_TYPE"),
])
def test_identical_wrong_app_or_document_type_still_flags_source_disagreement(
    field, wrong_value, expected_flag
):
    original, first, second = prepare()
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    first[0][field] = wrong_value
    second[0][field] = wrong_value
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert expected_flag in queue[0]["source_metadata_warning_flags"]
    assert audit["source_metadata_warning_references"] == 1
    assert audit["independently_verified_review_cycles"] == 0


@pytest.mark.parametrize("source_change,expected_flag", [
    ({"published_application_ids": "", "canonical_application_candidates": ""},
     "PUBLISHED_SOURCE_APPLICATION_ID_MISSING"),
    ({"source_letter_date_as_published": "2020-02-31"},
     "PUBLISHED_LETTER_DATE_MISSING_OR_INVALID"),
    ({"published_letter_type": ""}, "PUBLISHED_LETTER_TYPE_MISSING"),
])
def test_missing_or_invalid_published_metadata_needs_human_investigation(
    source_change, expected_flag
):
    original = example()
    original[0].update(source_change)
    first, second, _ = build_dual_review_packets(original)
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert expected_flag in queue[0]["source_metadata_warning_flags"]
    assert audit["model_eligible_records"] == 0


def test_source_warning_overlaps_reviewer_conflict_without_losing_counts():
    original, first, second = prepare()
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    first[0]["observed_action_date"] = "2020-01-02"
    second[0]["observed_action_date"] = "2020-01-03"
    comp = compare(original, first, second)
    assert comp["disagreeing_unverified_claims"] == 1
    queue, audit = build_review_triage(
        original, first, second, comp, pinned_index(), as_of=AS_OF,
    )
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert queue[0]["disputed_fields"] == "observed_action_date"
    assert audit["queue_status_counts"]["SOURCE_METADATA_DISCREPANCY"] == 1
    assert audit["source_metadata_warning_references"] == 1
    assert audit["model_eligible_records"] == 0


def test_single_complete_claim_with_wrong_metadata_remains_unreviewed():
    original, first, second = prepare()
    complete(first[0], "reviewer_a")
    first[0]["observed_action_date"] = "2020-01-02"
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert queue[0]["claimed_second_review_complete"] == "false"
    assert audit["source_metadata_warning_references"] == 1
    assert audit["independently_verified_review_cycles"] == 0


def test_correct_matching_metadata_remains_priority_four_not_verified():
    original, first, second = prepare()
    for rec in first:
        complete(rec, "reviewer_a")
    for rec in second:
        complete(rec, "reviewer_b")
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF,
    )
    assert all(r["triage_status"] == "MATCHING_TEXT_STILL_UNVERIFIED"
               and r["review_queue_priority"] == "4"
               and not r["source_metadata_warning_flags"] for r in queue)
    assert audit["source_metadata_warning_references"] == 0
    assert audit["independent_source_metadata_verified"] is False
    assert audit["prediction_probability"] is None


def test_matching_reviewers_with_wrong_application_trigger_priority_one():
    original, first, second = prepare()
    for review in first:
        complete(review, "reviewer_a")
    for review in second:
        complete(review, "reviewer_b")
    for review in (first[0], second[0]):
        review["observed_application_ids"] = "BLA000002"
    comparison = compare(original, first, second)
    assert comparison["matching_unverified_claims"] == 3
    queue, audit = build_review_triage(
        original, first, second, comparison, pinned_index(), as_of=AS_OF
    )
    assert queue[0]["source_record_sha256"] == "a" * 64
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert queue[0]["review_queue_priority"] == "1"
    assert queue[0]["source_metadata_warning_flags"] == (
        "REVIEWED_APPLICATION_NOT_IN_SOURCE_CANDIDATES"
    )
    assert audit["source_metadata_warning_references"] == 1
    assert audit["queue_status_counts"]["SOURCE_METADATA_DISCREPANCY"] == 1
    assert audit["queue_status_counts"]["MATCHING_TEXT_STILL_UNVERIFIED"] == 2
    assert audit["independent_source_metadata_verified"] is False
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["prediction_probability"] is None


def test_matching_wrong_date_and_letter_type_raise_both_metadata_warnings():
    original, first, second = prepare()
    for review in first:
        complete(review, "reviewer_a")
    for review in second:
        complete(review, "reviewer_b")
    for review in (first[0], second[0]):
        review["observed_action_date"] = "2020-01-02"
        review["observed_document_type"] = "TENTATIVE APPROVAL"
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF
    )
    flags = queue[0]["source_metadata_warning_flags"]
    assert "ACTION_DATE_DIFFERS_FROM_PUBLISHED_LETTER_DATE" in flags
    assert "DOCUMENT_TYPE_DIFFERS_FROM_PUBLISHED_LETTER_TYPE" in flags
    assert audit["source_metadata_warning_references"] == 1
    assert audit["model_eligible_records"] == 0


def test_metadata_warning_and_reviewer_conflict_overlap_without_double_counting():
    original, first, second = prepare()
    for review in first:
        complete(review, "reviewer_a")
    for review in second:
        complete(review, "reviewer_b")
    first[0]["observed_application_ids"] = "BLA000002"
    comparison = compare(original, first, second)
    assert comparison["disagreeing_unverified_claims"] == 1
    queue, audit = build_review_triage(
        original, first, second, comparison, pinned_index(), as_of=AS_OF
    )
    assert queue[0]["triage_status"] == "SOURCE_METADATA_DISCREPANCY"
    assert queue[0]["disputed_fields"] == "observed_application_ids"
    assert "REVIEWED_APPLICATION_NOT_IN_SOURCE_CANDIDATES" in (
        queue[0]["source_metadata_warning_flags"]
    )
    assert audit["queue_status_counts"]["SOURCE_METADATA_DISCREPANCY"] == 1
    assert sum(audit["queue_status_counts"].values()) == 3
    assert audit["independently_verified_review_cycles"] == 0


def test_missing_publication_metadata_is_a_warning_not_verified_evidence():
    original, first, second = prepare()
    original[0]["published_application_ids"] = ""
    original[0]["canonical_application_candidates"] = ""
    original[0]["source_letter_date_as_published"] = ""
    original[0]["published_letter_type"] = ""
    # Create packets from the modified, still unadjudicated source worksheet.
    first, second, _ = build_dual_review_packets(original)
    for review in first:
        complete(review, "reviewer_a")
    for review in second:
        complete(review, "reviewer_b")
    queue, audit = build_review_triage(
        original, first, second, compare(original, first, second),
        pinned_index(), as_of=AS_OF
    )
    flags = queue[0]["source_metadata_warning_flags"]
    assert "PUBLISHED_SOURCE_APPLICATION_ID_MISSING" in flags
    assert "PUBLISHED_LETTER_DATE_MISSING_OR_INVALID" in flags
    assert "PUBLISHED_LETTER_TYPE_MISSING" in flags
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["prediction_probability"] is None
