"""Synthetic-only FDA review-cycle claim quarantine and identity tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_review_triage import TRIAGE_FIELDS
from app.hop_fda_cycle_claim_register import (
    CLAIM_FIELDS, FIELDS, STATUS, prepare_claim_register, read_csv, render_csv,
    screen_claim_register,
)

CUTOFF = date(2026, 10, 25)


def queue_row(source="a", state="REVIEW_SUBMISSIONS_INCOMPLETE", priority="3"):
    row = {field: "" for field in TRIAGE_FIELDS}
    row.update({
        "review_queue_priority": priority,
        "triage_status": state,
        "source_record_sha256": source * 64,
        "fda_pdf_sha256": "b" * 64,
        "fda_pdf_url": "https://download.open.fda.gov/crl/fictional.pdf",
        "provisional_page_link": "https://download.open.fda.gov/crl/fictional.pdf#page=2",
        "claimed_first_review_complete": "false",
        "claimed_second_review_complete": "false",
        "review_reason": "TEST_ONLY",
    })
    return row


def sample():
    return [queue_row("a"), queue_row("c")]


def fill(row, *, app="NDA000001", cycle="1", action="COMPLETE_RESPONSE",
         action_day="2020-01-01"):
    row.update({
        "claimed_adjudicator_token": "claimed_reviewer_a",
        "claimed_original_letter_pages": "2-3",
        "claimed_application_id": app,
        "claimed_review_cycle": cycle,
        "claimed_fda_action_date": action_day,
        "claimed_fda_action_type": action,
        "claimed_indication": "Fictitious indication",
        "claimed_independent_fda_url": "https://www.fda.gov/drugs/fictional-case",
        "claimed_resolution_notes": "Synthetic unpublished report",
    })


def test_empty_register_is_blank_and_permanently_unverified():
    blank = prepare_claim_register(sample())
    assert len(blank) == 2
    assert tuple(blank[0]) == FIELDS
    assert all(blank_row["register_status"] == STATUS for blank_row in blank)
    assert all(not blank_row[field] for blank_row in blank for field in CLAIM_FIELDS)
    assert all(blank_row["model_eligible"] == "false" for blank_row in blank)
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_review_status_counts"] == {"NO_ADJUDICATION_CLAIM": 2}
    assert report["independently_verified_review_cycles"] == 0
    assert report["model_eligible_records"] == 0
    assert report["prediction_probability"] is None
    assert report["approval_rate"] is None
    assert report["complete_application_denominator_verified"] is False


def test_complete_claim_still_requires_original_source_adjudication():
    blank = prepare_claim_register(sample())
    fill(blank[0])
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_review_status_counts"] == {
        "COMPLETE_UNVERIFIED_CLAIM_NEEDS_SIGNOFF": 1,
        "NO_ADJUDICATION_CLAIM": 1,
    }
    assert report["adjudication_signatures_authenticated"] is False
    assert report["reviewer_identities_authenticated"] is False
    assert report["chronological_calibration_validated"] is False
    assert "claimed_reviewer_a" not in str(report)
    assert "Synthetic unpublished report" not in str(report)


def test_two_same_application_cycle_letters_require_manual_reconciliation():
    blank = prepare_claim_register(sample())
    fill(blank[0])
    fill(blank[1])
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_review_status_counts"] == {
        "MULTIPLE_LETTERS_SAME_CYCLE_NEEDS_RECONCILIATION": 2,
    }
    assert report["source_refs_with_duplicate_application_cycles"] == [
        "a" * 64, "c" * 64
    ]
    assert report["source_refs_with_conflicting_cycle_action_claims"] == []
    assert report["model_eligible_records"] == 0


def test_conflicting_action_claims_same_cycle_are_not_label_promoted():
    blank = prepare_claim_register(sample())
    fill(blank[0], action="COMPLETE_RESPONSE")
    fill(blank[1], action="APPROVED")
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_refs_with_duplicate_application_cycles"] == [
        "a" * 64, "c" * 64
    ]
    assert report["source_refs_with_conflicting_cycle_action_claims"] == [
        "a" * 64, "c" * 64
    ]
    assert report["independently_verified_review_cycles"] == 0
    assert report["prediction_probability"] is None


def test_nondecision_letter_must_not_be_approved_or_nonapproved_case():
    blank = prepare_claim_register(sample())
    fill(blank[0], action="NOT_AN_FDA_DECISION")
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_review_status_counts"]["NONDECISION_CLAIM_NEEDS_EXCLUSION_REVIEW"] == 1
    assert report["model_eligible_records"] == 0


def test_incomplete_claim_is_not_in_denominator():
    blank = prepare_claim_register(sample())
    blank[0]["claimed_adjudicator_token"] = "claimed_reviewer_a"
    report = screen_claim_register(sample(), blank, as_of=CUTOFF)
    assert report["source_review_status_counts"]["INCOMPLETE_ADJUDICATION_CLAIM"] == 1
    assert report["complete_application_denominator_verified"] is False


@pytest.mark.parametrize("field,value", [
    ("model_eligible", "true"),
    ("register_status", "VERIFIED"),
    ("fda_pdf_url", "https://fake.example/fictional.pdf"),
    ("claimed_original_letter_pages", "7-3"),
    ("claimed_application_id", "BLAABCDEF"),
    ("claimed_review_cycle", "0"),
    ("claimed_fda_action_date", "2026-12-31"),
    ("claimed_fda_action_date", "2020-14-05"),
    ("claimed_fda_action_type", "POSTHOC APPROVED"),
    ("claimed_independent_fda_url", "https://www.fda.gov.evil.example/foo"),
    ("claimed_resolution_notes", "=HYPERLINK(\"https://evil.test\")"),
])
def test_tampering_or_invalid_full_claim_fields_fail_closed(field, value):
    queue = sample()
    blank = prepare_claim_register(queue)
    fill(blank[0])
    blank[0][field] = value
    with pytest.raises(ValueError):
        screen_claim_register(queue, blank, as_of=CUTOFF)


def test_duplicate_missing_and_foreign_reference_fail_closed():
    queue = sample()
    blank = prepare_claim_register(queue)
    with pytest.raises(ValueError):
        screen_claim_register(queue, blank[:1], as_of=CUTOFF)
    with pytest.raises(ValueError):
        screen_claim_register(queue, [blank[0], deepcopy(blank[0])], as_of=CUTOFF)
    foreign = deepcopy(blank[1])
    foreign["source_record_sha256"] = "d" * 64
    with pytest.raises(ValueError):
        screen_claim_register(queue, [blank[0], foreign], as_of=CUTOFF)


def test_invalid_source_worklist_priority_or_pdf_rejected_before_prep():
    queue = sample()
    queue[0]["review_queue_priority"] = "1"
    with pytest.raises(ValueError):
        prepare_claim_register(queue)
    queue = sample()
    queue[0]["fda_pdf_url"] = "https://fake.test/crl/fictional.pdf"
    with pytest.raises(ValueError):
        prepare_claim_register(queue)


def test_strict_csv_headers_and_no_extra_fields(tmp_path):
    blank = prepare_claim_register(sample())
    path = tmp_path / "register.csv"
    path.write_text(render_csv(blank, FIELDS), encoding="utf-8")
    assert read_csv(path, FIELDS) == blank
    path.write_text("wrong,headers\nx,y\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(path, FIELDS)
    path.write_text(render_csv(blank, FIELDS) + "unexpected,extra,cells\n",
                    encoding="utf-8")
    with pytest.raises(ValueError):
        read_csv(path, FIELDS)
