"""Single-case tests for original FDA KEYNOTE-024 research-stage evidence.

The real original letter is sourced, but neither the source content nor
reviewer claims are independently adjudicated by these tests.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.hop_fda_pilot_case_audit import audit_pilot_dossier, load_pilot_dossier

PILOT = (
    Path(__file__).resolve().parents[1] / "app" / "research_sources"
    / "hop_keynote024_primary_letter_pilot_research.json"
)


def pilot():
    return load_pilot_dossier(PILOT)


def test_research_pilot_has_correct_original_fda_case_but_no_model_clearance():
    report = audit_pilot_dossier(pilot())
    assert report["original_fda_pdf_references"] == 1
    assert report["distinct_supplement_claims_in_same_letter"] == 2
    assert report["separately_attributed_supplements"] == ["S-8", "S-12"]
    assert report["keynote024_predecision_publication_candidate"] is True
    assert report["journal_issue_after_fda_action"] is True
    assert report["independent_human_review_complete"] is False
    assert report["independently_verified_fda_outcome_labels"] == 0
    assert report["model_eligible_records"] == 0
    assert report["probability"] is None
    assert report["approval_rate"] is None
    assert report["readiness"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(("section", "key", "value"), [
    ("document", "source_pdf_sha256", "a" * 64),
    ("document", "primary_application", "BLA125515"),
    ("document", "reference_id", "4009999"),
    ("document", "electronic_signature_date", "2016-10-23"),
    ("document", "pdufa_target_date", "2016-10-24"),
    ("document", "actual_public_web_release_date", "2016-10-24"),
    ("document", "independent_reviewer_attestation", "SIGNED"),
    ("document", "official_fda_approval_letter_url",
     "https://www.accessdata.fda.gov.evil.test/drugsatfda_docs/appletter/2016/fake.pdf"),
    ("trial_predecision_publication_candidate", "ahead_of_print_date", "2016-11-10"),
    ("trial_predecision_publication_candidate", "issue_date", "2016-10-08"),
    ("trial_predecision_publication_candidate", "first_public_snapshot_independently_archived", True),
    ("trial_predecision_publication_candidate", "point_in_time_feature_set_complete", True),
    ("review_and_model_gates", "reviewer_one_identity_verified", True),
    ("review_and_model_gates", "reviewer_two_identity_verified", True),
    ("review_and_model_gates", "independent_document_page_adjudication_complete", True),
    ("review_and_model_gates", "exact_application_supplement_action_adjudicated", True),
    ("review_and_model_gates", "complete_fda_approval_and_nonapproval_cohort_verified", True),
    ("review_and_model_gates", "model_eligible_records", 1),
    ("review_and_model_gates", "independently_verified_review_cycle_outcomes", 2),
    ("review_and_model_gates", "predicted_probability", 0.89),
    ("review_and_model_gates", "approval_rate", 0.9),
    ("review_and_model_gates", "trading_signal_allowed", True),
])
def test_tampering_or_forging_original_source_and_readiness_fails_closed(
    section, key, value,
):
    source = pilot()
    source[section][key] = value
    with pytest.raises(ValueError):
        audit_pilot_dossier(source)


def test_supplement_identity_not_collapsed_into_original_bla():
    original = pilot()
    source = deepcopy(original)
    source["supplements"] = [source["supplements"][1]]
    with pytest.raises(ValueError):
        audit_pilot_dossier(source)
    source = deepcopy(original)
    source["supplements"][0]["supplement"] = "S-12"
    with pytest.raises(ValueError):
        audit_pilot_dossier(source)
    source = deepcopy(original)
    source["supplements"][1]["key_trial"] = "KEYNOTE-042"
    with pytest.raises(ValueError):
        audit_pilot_dossier(source)


def test_two_document_actions_cannot_be_promoted_by_a_boolean():
    source = pilot()
    source["supplements"][1]["independently_adjudicated"] = True
    with pytest.raises(ValueError):
        audit_pilot_dossier(source)


def test_file_loader_rejects_missing_or_non_object_json(tmp_path):
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps([]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_pilot_dossier(path)
