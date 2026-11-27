"""Offline source-review packet tests use fictitious hashes and references only."""
import csv
from pathlib import Path

import pytest

from app.hop_fda_page_review_worksheet import COLUMNS
from app.hop_fda_dual_review_packets import (
    PACKET_COLUMNS, STATUS, build_dual_review_packets,
    load_unreviewed_worksheet, packet_csv,
)


def unreviewed(hash_char="a", pdf_char="b"):
    row = {col: "" for col in COLUMNS}
    row.update({
        "review_priority": "3",
        "review_reason": "SINGLE_STRONG_PAGE_CANDIDATE_NEEDS_INDEPENDENT_REVIEW",
        "source_record_sha256": hash_char * 64,
        "fda_pdf_sha256": pdf_char * 64,
        "fda_pdf_url": "https://download.open.fda.gov/crl/synthetic.pdf",
        "provisional_page_link": "https://download.open.fda.gov/crl/synthetic.pdf#page=2",
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


def test_creates_two_identical_scope_blind_unreviewed_packets():
    one, two, audit = build_dual_review_packets([unreviewed(), unreviewed("c", "b")])
    assert len(one) == len(two) == 2
    assert all(row["packet_role"] == "FIRST" for row in one)
    assert all(row["packet_role"] == "SECOND" for row in two)
    for x, y in zip(one, two):
        assert x["source_record_sha256"] == y["source_record_sha256"]
        assert x["packet_status"] == y["packet_status"] == STATUS
        for k in ("reviewer_id", "observed_pdf_sha256", "observed_letter_pages",
                  "observed_application_ids", "observed_action_date",
                  "observed_document_type", "observed_review_cycle", "source_evidence_notes"):
            assert x[k] == y[k] == ""
    assert audit["published_letter_references"] == 2
    assert audit["independent_review_pairs_completed"] == 0
    assert audit["reviewer_identity_verified"] is False
    assert audit["fda_review_cycle_outcomes_verified"] == 0
    assert audit["complete_application_denominator_verified"] is False
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None


def test_csv_export_contains_only_unreviewed_blank_fields():
    first, _, _ = build_dual_review_packets([unreviewed()])
    contents = packet_csv(first)
    assert "packet_role,packet_status" in contents
    assert list(csv.DictReader(contents.splitlines()))[0]["reviewer_id"] == ""
    assert tuple(csv.DictReader(contents.splitlines()).fieldnames) == PACKET_COLUMNS


def test_csv_loader_requires_exact_headers_and_no_extra_columns(tmp_path):
    path = Path(tmp_path) / "worksheet.csv"
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow(unreviewed())
    assert load_unreviewed_worksheet(path) == [unreviewed()]
    path.write_text("fake,headers\na,b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_unreviewed_worksheet(path)


@pytest.mark.parametrize("field,value", [
    ("first_reviewer", "REVIEWER-X"),
    ("second_reviewer_evidence_notes", "already filled"),
    ("independent_review_complete", "True"),
    ("model_eligible", "True"),
    ("regulatory_outcome_verified", "True"),
    ("review_status", "ADJUDICATED"),
    ("source_record_sha256", "bad"),
    ("fda_pdf_url", "https://download.open.fda.gov.evil.test/crl/a.pdf"),
    ("provisional_page_link", "https://other.test/fake#page=2"),
    ("published_application_ids", "=HYPERLINK(\"https://evil.test\")"),
    ("candidate_pages_1_based", "2,2"),
    ("candidate_page_count", "2"),
])
def test_fails_closed_on_promoted_untrusted_or_malformed_source_fields(field, value):
    row = unreviewed()
    row[field] = value
    with pytest.raises(ValueError):
        build_dual_review_packets([row])


def test_duplicate_source_hash_fails_closed():
    with pytest.raises(ValueError):
        build_dual_review_packets([unreviewed(), unreviewed()])


def test_cannot_export_packet_after_human_edits_without_explicit_reconciliation():
    first, _, _ = build_dual_review_packets([unreviewed()])
    first[0]["observed_action_date"] = "2020-01-01"
    with pytest.raises(ValueError):
        packet_csv(first)


def test_no_source_rows_does_not_fake_reviewer_progress():
    with pytest.raises(ValueError):
        build_dual_review_packets([])
