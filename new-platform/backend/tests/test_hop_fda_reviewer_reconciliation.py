"""Reviewer reconciliation tests use only entirely fabricated FDA records."""
from __future__ import annotations

import csv
from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_page_review_worksheet import COLUMNS
from app.hop_fda_dual_review_packets import (
    PACKET_COLUMNS, build_dual_review_packets,
)
from app.hop_fda_reviewer_reconciliation import (
    load_completed_or_blank_packet, reconcile_review_claims,
)

AS_OF = date(2026, 10, 25)


def original(source="a", pdf="b"):
    row = {k: "" for k in COLUMNS}
    row.update({
        "review_priority": "3",
        "review_reason": "SINGLE_STRONG_PAGE_CANDIDATE_NEEDS_INDEPENDENT_REVIEW",
        "source_record_sha256": source * 64,
        "fda_pdf_sha256": pdf * 64,
        "fda_pdf_url": "https://download.open.fda.gov/crl/fictional.pdf",
        "provisional_page_link": "https://download.open.fda.gov/crl/fictional.pdf#page=2",
        "published_application_ids": "NDA000001",
        "canonical_application_candidates": "NDA000001",
        "source_letter_date_as_published": "2020-01-01",
        "published_letter_type": "COMPLETE RESPONSE",
        "candidate_status": "DATE_AND_ID_PAGE_CANDIDATES",
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
    return row


def make_two(count=1):
    sources = [original("a"), original("c")] if count == 2 else [original()]
    first, second, _ = build_dual_review_packets(sources)
    return sources, first, second


def complete(row, reviewer):
    row.update({
        "reviewer_id": reviewer,
        "observed_pdf_sha256": row["fda_pdf_sha256"],
        "observed_letter_pages": "2-3",
        "observed_application_ids": "NDA000001",
        "observed_action_date": "2020-01-01",
        "observed_document_type": "COMPLETE RESPONSE",
        "observed_review_cycle": "1",
        "source_evidence_notes": "Fictitious test observation",
    })


def test_blank_reviewers_never_count_as_reviewed():
    source, first, second = make_two(2)
    result = reconcile_review_claims(source, first, second, as_of=AS_OF)
    assert result["source_reference_rows"] == 2
    assert result["two_reported_complete_claims"] == 0
    assert result["incomplete_or_missing_reviewer_claims"] == 2
    assert result["reviewer_identity_authenticated"] is False
    assert result["independently_verified_review_cycles"] == 0
    assert result["model_eligible_records"] == 0
    assert result["prediction_probability"] is None


def test_agreed_claims_are_never_verified_even_when_two_tokens_differ():
    source, first, second = make_two()
    complete(first[0], "reviewer_a")
    complete(second[0], "reviewer_b")
    second[0]["observed_application_ids"] = "NDA-000001"
    result = reconcile_review_claims(source, first, second, as_of=AS_OF)
    assert result["matching_unverified_claims"] == 1
    assert result["disagreeing_unverified_claims"] == 0
    assert result["claimed_distinct_reviewer_tokens"] == 2
    assert result["reviewer_independence_confirmed"] is False
    assert result["complete_application_denominator_verified"] is False
    assert result["readiness"] == "REVIEW_REQUIRED"
    assert result["approval_rate"] is None


def test_divergent_action_dates_flagged_without_leaking_notes_or_identities():
    source, first, second = make_two()
    complete(first[0], "reviewer_a")
    complete(second[0], "reviewer_b")
    second[0]["observed_action_date"] = "2020-01-02"
    second[0]["source_evidence_notes"] = "SECRET_SECOND_REVIEWER_NOTE"
    result = reconcile_review_claims(source, first, second, as_of=AS_OF)
    assert result["disagreeing_unverified_claims"] == 1
    assert result["disagreements_needing_human_resolution"] == [
        {"source_record_sha256": "a" * 64, "disputed_fields": ["observed_action_date"]}
    ]
    assert "reviewer_a" not in str(result)
    assert "reviewer_b" not in str(result)
    assert "SECRET_SECOND_REVIEWER_NOTE" not in str(result)
    assert result["independently_verified_review_cycles"] == 0


def test_a_partial_submission_is_not_a_confirmed_match():
    source, first, second = make_two()
    complete(first[0], "reviewer_a")
    second[0]["reviewer_id"] = "reviewer_b"
    result = reconcile_review_claims(source, first, second, as_of=AS_OF)
    assert result["incomplete_or_missing_reviewer_claims"] == 1
    assert result["matching_unverified_claims"] == 0


@pytest.mark.parametrize("change", [
    "same_reviewer", "tamper_source", "duplicate", "missing_source",
    "extra_source", "wrong_role", "claim_promotion",
    "different_pdf_sha", "wrong_date", "future_date", "reverse_pages",
    "bad_applications", "formula_notes", "multiple_reviewer_tokens",
])
def test_source_identity_and_claim_safety_fail_closed(change):
    source, first, second = make_two(2)
    for row in first:
        complete(row, "reviewer_a")
    for row in second:
        complete(row, "reviewer_b")
    if change == "same_reviewer":
        for row in second:
            row["reviewer_id"] = "reviewer_a"
    elif change == "tamper_source":
        first[0]["published_letter_type"] = "APPROVED"
    elif change == "duplicate":
        first[1] = deepcopy(first[0])
    elif change == "missing_source":
        second.pop()
    elif change == "extra_source":
        first.append(deepcopy(first[0]))
        first[-1]["source_record_sha256"] = "e" * 64
    elif change == "wrong_role":
        first[0]["packet_role"] = "SECOND"
    elif change == "claim_promotion":
        first[0]["packet_status"] = "VERIFIED"
    elif change == "different_pdf_sha":
        first[0]["observed_pdf_sha256"] = "f" * 64
    elif change == "wrong_date":
        first[0]["observed_action_date"] = "2020-13-01"
    elif change == "future_date":
        first[0]["observed_action_date"] = "2027-01-01"
    elif change == "reverse_pages":
        first[0]["observed_letter_pages"] = "5-2"
    elif change == "bad_applications":
        first[0]["observed_application_ids"] = "NDA000001;NDA-000001"
    elif change == "formula_notes":
        first[0]["source_evidence_notes"] = "=SUM(A1:A2)"
    elif change == "multiple_reviewer_tokens":
        first[1]["reviewer_id"] = "reviewer_c"
    with pytest.raises(ValueError):
        reconcile_review_claims(source, first, second, as_of=AS_OF)


def test_strict_csv_reader_rejects_unexpected_columns_and_extra_cells(tmp_path):
    source, first, _ = make_two()
    path = tmp_path / "first.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=PACKET_COLUMNS)
        writer.writeheader()
        writer.writerows(first)
    assert load_completed_or_blank_packet(path) == first
    with path.open("a", encoding="utf-8") as fh:
        fh.write("unexpected,extra,column\n")
    with pytest.raises(ValueError):
        load_completed_or_blank_packet(path)


def test_incomplete_and_disputed_claims_reconcile_by_original_reference_not_sort_order():
    source, first, second = make_two(2)
    for row in first:
        complete(row, "reviewer_a")
    for row in second:
        complete(row, "reviewer_b")
    second.reverse()
    second[0]["observed_review_cycle"] = "2"
    result = reconcile_review_claims(source, first, second, as_of=AS_OF)
    assert result["source_reference_rows"] == 2
    assert result["matching_unverified_claims"] == 1
    assert result["disagreeing_unverified_claims"] == 1
    assert result["disagreements_needing_human_resolution"][0][
        "source_record_sha256"] == "c" * 64
