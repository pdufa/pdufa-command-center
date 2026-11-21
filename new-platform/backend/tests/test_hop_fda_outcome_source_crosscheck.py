"""Synthetic historical-to-cycle tests; a match is never validated science."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest

from app.hop_fda_review_triage import TRIAGE_FIELDS
from app.hop_fda_cycle_claim_register import prepare_claim_register
from app.hop_fda_outcome_source_crosscheck import crosscheck_historical_outcome_claims
from app.hop_outcomes_import import HistoricalOutcomeRecord

AS_OF = date(2026, 10, 25)
URL = "https://download.open.fda.gov/crl/fictional.pdf"
EVIDENCE = "https://www.fda.gov/drugs/fictional-case"


def source(sid="a"):
    item = {field: "" for field in TRIAGE_FIELDS}
    item.update({
        "review_queue_priority": "3",
        "triage_status": "REVIEW_SUBMISSIONS_INCOMPLETE",
        "source_record_sha256": sid * 64,
        "fda_pdf_sha256": "b" * 64,
        "fda_pdf_url": URL,
        "provisional_page_link": URL + "#page=2",
        "review_reason": "SYNTHETIC_TEST_NOT_FDA_ADJUDICATION",
        "claimed_first_review_complete": "false",
        "claimed_second_review_complete": "false",
    })
    return item


def historical(case="fictional-case", app="NDA000001", cycle=1,
               day=date(2020, 1, 1), label="COMPLETE_RESPONSE", url=URL):
    return HistoricalOutcomeRecord(
        case_id=case, application_id=app, review_cycle=cycle,
        drug_name="Fictional drug", sponsor="Fictional sponsor",
        indication="Fictional indication", therapeutic_area="Fictional",
        modality="Small molecule", phase=3, decision_date=day, outcome=label,
        public_features_as_of=day - timedelta(days=100),
        evidence_as_of=day + timedelta(days=1), source_url=url,
        source_title="Fabricated FDA source for tests",
    )


def intake(*records):
    return {
        "status": "SCHEMA_VALIDATED_REVIEW_REQUIRED" if records else "REVIEW_REQUIRED",
        "accepted": len(records), "rejected": 0, "records": list(records),
        "model_eligible_records": 0, "independently_verified": False,
        "probability": None, "rejections": [],
    }


def fill(row, *, app="NDA000001", cycle="1",
         day="2020-01-01", label="COMPLETE_RESPONSE"):
    row.update({
        "claimed_adjudicator_token": "claimant_123",
        "claimed_original_letter_pages": "2-3",
        "claimed_application_id": app,
        "claimed_review_cycle": cycle,
        "claimed_fda_action_date": day,
        "claimed_fda_action_type": label,
        "claimed_indication": "Fictional indication",
        "claimed_independent_fda_url": EVIDENCE,
        "claimed_resolution_notes": "Only synthetic claim; not adjudicated.",
    })


def run(rows=None, records=None):
    rows = [source()] if rows is None else rows
    records = [] if records is None else records
    blank = prepare_claim_register(rows)
    return rows, blank, intake(*records)


def test_empty_historical_template_reports_zero_and_blocks_model_eligibility():
    rows, claims, imported = run()
    audit = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert audit["staged_historical_outcome_rows"] == 0
    assert audit["independent_fda_review_cycle_decisions_verified"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    assert audit["complete_fda_approval_nonapproval_denominator_verified"] is False


def test_exactly_matching_unverified_claim_remains_review_required():
    record = historical()
    rows, claims, imported = run(records=[record])
    fill(claims[0])
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert result["case_diagnostics"][0]["diagnostic_reasons"] == [
        "MATCHING_UNVERIFIED_CLAIMS_REQUIRES_HUMAN_ADJUDICATION"
    ]
    assert result["case_diagnostics"][0]["model_eligible"] is False
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["readiness"] == "REVIEW_REQUIRED"


def test_missing_candidate_cycle_and_unreviewed_cycle_are_not_false_matches():
    record = historical()
    rows, claims, imported = run(records=[record])
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert result["case_diagnostics"][0]["diagnostic_reasons"] == [
        "NO_MATCHING_PUBLISHED_SOURCE_CYCLE_CLAIM"
    ]


@pytest.mark.parametrize("change, expected", [
    ("application", "NO_MATCHING_PUBLISHED_SOURCE_CYCLE_CLAIM"),
    ("cycle", "NO_MATCHING_PUBLISHED_SOURCE_CYCLE_CLAIM"),
    ("date", "FDA_ACTION_DATE_MISMATCH"),
    ("label", "FDA_ACTION_LABEL_MISMATCH"),
    ("source_url", "OUTCOME_SOURCE_URL_NOT_LINKED_TO_REVIEW_CLAIM"),
])
def test_detects_offline_historical_vs_cycle_claim_differences(change, expected):
    record = historical()
    if change == "source_url":
        record = replace(record, source_url="https://www.fda.gov/drugs/different-source")
    rows, claims, imported = run(records=[record])
    fill(claims[0])
    if change == "application":
        claims[0]["claimed_application_id"] = "BLA000002"
    elif change == "cycle":
        claims[0]["claimed_review_cycle"] = "2"
    elif change == "date":
        claims[0]["claimed_fda_action_date"] = "2020-01-02"
    elif change == "label":
        claims[0]["claimed_fda_action_type"] = "APPROVED"
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert expected in result["case_diagnostics"][0]["diagnostic_reasons"]
    assert result["independent_fda_review_cycle_decisions_verified"] == 0


def test_duplicate_letter_sources_cannot_fake_multiple_verified_decisions():
    record = historical()
    rows, claims, imported = run(rows=[source("a"), source("c")], records=[record])
    for claim in claims:
        fill(claim)
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert "AMBIGUOUS_MULTIPLE_PUBLISHED_LETTER_REFERENCES" in (
        result["case_diagnostics"][0]["diagnostic_reasons"]
    )
    assert result["case_diagnostics"][0]["candidate_source_references"] == 2
    assert result["model_eligible_records"] == 0


def test_conflicting_duplicate_letter_labels_raise_both_diagnostics():
    record = historical()
    rows, claims, imported = run(rows=[source("a"), source("c")], records=[record])
    fill(claims[0], label="COMPLETE_RESPONSE")
    fill(claims[1], label="APPROVED")
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    reasons = result["case_diagnostics"][0]["diagnostic_reasons"]
    assert "AMBIGUOUS_MULTIPLE_PUBLISHED_LETTER_REFERENCES" in reasons
    assert "CONFLICTING_SOURCE_ACTION_OR_DATE_CLAIMS" in reasons
    assert result["prediction_probability"] is None


def test_not_decision_letter_never_supports_an_outcome_label():
    record = historical()
    rows, claims, imported = run(records=[record])
    fill(claims[0], label="NOT_AN_FDA_DECISION")
    result = crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    assert "NO_MATCHING_PUBLISHED_SOURCE_CYCLE_CLAIM" in (
        result["case_diagnostics"][0]["diagnostic_reasons"]
    )


def test_refuses_forged_outcome_model_clearance_and_tampered_source():
    rows, claims, imported = run(records=[historical()])
    fill(claims[0])
    imported["model_eligible_records"] = 1
    with pytest.raises(ValueError):
        crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    imported["model_eligible_records"] = 0
    claims[0]["model_eligible"] = "true"
    with pytest.raises(ValueError):
        crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)


def test_refuses_duplicate_historical_review_cycles_and_time_leakage():
    rows, claims, imported = run(records=[
        historical(case="one"), historical(case="two")
    ])
    with pytest.raises(ValueError):
        crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
    rows, claims, imported = run(records=[replace(
        historical(), public_features_as_of=date(2020, 1, 1),
    )])
    with pytest.raises(ValueError):
        crosscheck_historical_outcome_claims(imported, rows, claims, as_of=AS_OF)
