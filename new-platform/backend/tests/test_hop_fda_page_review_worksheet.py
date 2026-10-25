import csv
import io
from copy import deepcopy

import pytest

from app.hop_fda_page_review_worksheet import (
    build_pdf_page_review_worksheet, worksheet_csv
)

URL = "https://download.open.fda.gov/crl/212887Orig1s000%2C212888Orig1s000OtherActionLtrs.pdf"
PAGE_STATUS = "FDA_SHARED_PDF_PAGE_CANDIDATES_REQUIRE_HUMAN_ADJUDICATION"
GROUP_STATUS = "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"


def source(char, app):
    return {
        "source_record_sha256": char * 64,
        "source_letter_date_as_published": "12/19/2019",
        "published_letter_type": "COMPLETE RESPONSE",
        "application_ids_as_published": ["NDA " + app[-6:]],
        "canonical_application_candidates": [app],
        "official_fda_document_url": URL,
    }


def candidate(s, page, strong=True):
    return {
        "source_record_sha256": s["source_record_sha256"],
        "source_letter_date_as_published": s["source_letter_date_as_published"],
        "application_ids_as_published": s["application_ids_as_published"],
        "candidate_status": "DATE_AND_ID_PAGE_CANDIDATES" if strong else "ID_ONLY_PAGE_CANDIDATES",
        "candidate_pages": [{
            "page_number_1_based": page,
            "application_id_token_found": True,
            "published_letter_date_token_found": strong,
            "evidence_grade": "SAME_PAGE_ID_AND_LETTER_DATE" if strong else "PAGE_ID_ONLY",
            "provisional_only": True,
        }],
        "candidate_page_count": 1,
        "proposed_letter_page_range": None,
        "individual_letter_page_range_independently_verified": False,
        "effective_fda_action_date_independently_verified": False,
        "regulatory_outcome_independently_verified": False,
        "model_eligible": False,
    }


def fixture():
    a = source("a", "NDA212887")
    b = source("b", "NDA212888")
    digest = "f" * 64
    grouping = {
        "status": GROUP_STATUS,
        "records": [{
            "official_fda_pdf_sha256": digest,
            "official_fda_pdf_url": URL,
            "source_letter_records": [a,b],
            "published_letter_record_count": 2,
            "multiple_application_candidates_in_one_pdf": True,
            "same_source_date_and_type_collision": True,
            "model_eligible": False,
            "individual_letter_page_ranges_verified": False,
            "individual_review_cycle_outcomes_verified": False,
        }],
    }
    page_data = {
        "status": PAGE_STATUS,
        "records": [{
            "official_fda_pdf_sha256": digest,
            "official_fda_pdf_url": URL,
            "source_letter_record_count": 2,
            "page_count": 12,
            "letter_page_candidates": [candidate(a, 2), candidate(b, 8, False)],
            "model_eligible": False,
            "document_page_ranges_independently_verified": False,
            "review_cycle_outcomes_independently_verified": False,
        }]
    }
    return page_data, grouping


def test_worksheet_preserves_source_hashes_and_explicit_not_adjudicated():
    pages, shared = fixture()
    rows, audit = build_pdf_page_review_worksheet(pages, shared)
    assert len(rows) == 2
    assert audit["published_letter_rows"] == 2
    assert audit["shared_pdf_groups"] == 1
    assert audit["review_priority_counts"] == {"1": 2}
    assert audit["candidate_status_counts"] == {
        "DATE_AND_ID_PAGE_CANDIDATES": 1, "ID_ONLY_PAGE_CANDIDATES": 1}
    assert audit["model_eligible_records"] == 0
    assert audit["independently_verified_review_cycle_outcomes"] == 0
    assert audit["prediction_probability"] is None
    assert all(row["cross_application_pdf"] is True for row in rows)
    assert all(row["independent_review_complete"] is False for row in rows)
    assert all(row["regulatory_outcome_verified"] is False for row in rows)
    assert all(row["review_status"] == "NOT_ADJUDICATED" for row in rows)
    assert rows[0]["source_record_sha256"] == "a" * 64
    assert rows[0]["provisional_page_link"] == URL + "#page=2"
    assert rows[1]["provisional_page_link"] == URL + "#page=8"
    parsed = list(csv.DictReader(io.StringIO(worksheet_csv(rows))))
    assert len(parsed) == 2
    assert parsed[0]["model_eligible"] == "False"
    assert parsed[0]["fda_pdf_sha256"] == "f" * 64
    assert parsed[0]["candidate_pages_1_based"] == "2"


def test_weak_page_match_can_never_be_labeled_as_strong():
    pages, shared = fixture()
    match = pages["records"][0]["letter_page_candidates"][1]["candidate_pages"][0]
    match["evidence_grade"] = "SAME_PAGE_ID_AND_LETTER_DATE"
    with pytest.raises(ValueError, match="weak page match"):
        build_pdf_page_review_worksheet(pages, shared)


@pytest.mark.parametrize("alter", [
    lambda p, s: p["records"][0].update({"model_eligible": True}),
    lambda p, s: s["records"][0].update({"individual_review_cycle_outcomes_verified": True}),
    lambda p, s: p["records"][0]["letter_page_candidates"][0].update(
        {"effective_fda_action_date_independently_verified": True}),
    lambda p, s: p["records"][0]["letter_page_candidates"][0].update(
        {"proposed_letter_page_range": [1,3]}),
    lambda p, s: p["records"][0]["letter_page_candidates"][0]["candidate_pages"][0].update(
        {"page_number_1_based": 999}),
    lambda p, s: p["records"][0]["letter_page_candidates"][0].update(
        {"application_ids_as_published": ["NDA 999999"]}),
    lambda p, s: p["records"][0].update({"official_fda_pdf_url": "https://evil.example/x.pdf"}),
    lambda p, s: p["records"][0]["letter_page_candidates"][1].update(
        {"source_record_sha256": "a" * 64}),
])
def test_source_tampering_or_false_outcomes_fail_closed(alter):
    pages, shared = fixture()
    alter(pages, shared)
    with pytest.raises(ValueError):
        build_pdf_page_review_worksheet(pages, shared)


def test_distinct_weak_unmatched_and_multi_strong_review_priorities():
    pages, shared = fixture()
    group = shared["records"][0]
    group["multiple_application_candidates_in_one_pdf"] = False
    group["same_source_date_and_type_collision"] = False
    rows, _ = build_pdf_page_review_worksheet(pages, shared)
    assert [r["review_priority"] for r in rows] == [3,5]
    assert rows[0]["review_reason"] == "SINGLE_STRONG_PAGE_CANDIDATE_NEEDS_INDEPENDENT_REVIEW"
    source_row = pages["records"][0]["letter_page_candidates"][0]
    source_row["candidate_pages"].append({
        "page_number_1_based": 4,
        "application_id_token_found": True,
        "published_letter_date_token_found": True,
        "evidence_grade": "SAME_PAGE_ID_AND_LETTER_DATE",
        "provisional_only": True
    })
    source_row["candidate_page_count"] = 2
    rows, _ = build_pdf_page_review_worksheet(pages, shared)
    assert [r["review_priority"] for r in rows] == [4,5]
    assert rows[0]["provisional_page_link"] == ""


def test_completed_review_cannot_export_as_unverified_csv():
    pages, shared = fixture()
    rows, _ = build_pdf_page_review_worksheet(pages, shared)
    rows[0]["independent_review_complete"] = True
    with pytest.raises(ValueError, match="cannot export promoted"):
        worksheet_csv(rows)
