"""Synthetic one-reviewer FDA source checks; no FDA outcomes are certified."""
import copy
from datetime import date

import pytest
from app.hop_fda_single_primary_review import (
    prepare_single_primary_batches, reconcile_single_primary_claims,
    AWAITING, ESCALATE, PRELIMINARY,
)
from test_hop_fda_private_review_batches import realistic_synthetic_queue


def _source():
    return realistic_synthetic_queue()[0]


def _claim(row, *, app=None, cycle="1"):
    row.update({
        "reviewer_token": "PrimaryTest1",
        "observed_application_id": app or row["application_id_candidate"] or "NDA999999",
        "observed_submission_class": "ORIGINAL",
        "observed_letter_pages": "1-2",
        "observed_fda_action_date": "2025-02-01",
        "observed_document_class": "APPROVAL",
        "observed_review_cycle": cycle,
        "source_evidence_notes": "Original PDF still requires independent signoff",
    })


def test_seven_first_only_batches_preserve_source_counts_and_unverified_status():
    batches, summary = prepare_single_primary_batches(_source())
    assert [b["source_references"] for b in batches] == [17, 19, 20, 20, 20, 20, 8]
    assert summary["published_letter_references"] == 124
    assert summary["research_group_count"] == 101
    assert summary["second_review_files_exported"] == 0
    assert summary["primary_reviewer_slots"] == 1
    assert summary["independent_second_reviewer_required_for_all"] is False
    assert summary["model_eligible_records"] == 0
    assert summary["prediction_probability"] is None
    assert all("second_blank_reviewer_sources" not in b for b in batches)


def test_one_reviewer_triage_counts_are_not_fda_outcomes():
    original = _source()
    submitted = copy.deepcopy(original)
    _claim(submitted[0])     # Ambiguous original application
    _claim(submitted[17])    # Provisional original-application match
    summary = reconcile_single_primary_claims(
        original, submitted, as_of=date(2026, 10, 25))
    assert summary["single_reviewer_record_counts"] == {
        AWAITING: 122, ESCALATE: 1, PRELIMINARY: 1,
    }
    assert summary["reviewer_identity_authenticated"] is False
    assert summary["independently_verified_original_fda_actions"] == 0
    assert summary["model_eligible_records"] == 0
    assert summary["prediction_probability"] is None
    assert "PrimaryTest1" not in str(summary)


@pytest.mark.parametrize("tamper", [
    "source", "role", "eligible", "auth", "decision", "date",
    "formula", "duplicate", "partial_cohort", "multiple_tokens",
    "unknown_field", "page_reversed",
])
def test_invalid_single_reviewer_claims_fail_closed(tamper):
    original = _source()
    submitted = copy.deepcopy(original)
    _claim(submitted[17])
    row = submitted[17]
    if tamper == "source":
        row["source_lock_sha256"] = "0" * 64
    elif tamper == "role":
        row["packet_role"] = "SECOND"
    elif tamper == "eligible":
        row["model_eligible"] = True
    elif tamper == "auth":
        row["reviewer_authentication_verified"] = True
    elif tamper == "decision":
        row["independent_regulatory_adjudication_verified"] = True
    elif tamper == "date":
        row["observed_fda_action_date"] = "2026-11-01"
    elif tamper == "formula":
        row["source_evidence_notes"] = "=UNTRUSTED"
    elif tamper == "duplicate":
        submitted[18] = copy.deepcopy(row)
    elif tamper == "partial_cohort":
        submitted.pop()
    elif tamper == "multiple_tokens":
        _claim(submitted[18])
        submitted[18]["reviewer_token"] = "PrimaryTestOther"
    elif tamper == "unknown_field":
        row["release_probability"] = 1
    elif tamper == "page_reversed":
        row["observed_letter_pages"] = "9-2"
    with pytest.raises(ValueError):
        reconcile_single_primary_claims(
            original, submitted, as_of=date(2026, 10, 25))


def test_legacy_dual_review_path_remains_unchanged():
    from app.hop_fda_identity_gap_dual_review import ROLE
    assert ROLE == ("FIRST", "SECOND")
