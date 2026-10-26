"""Synthetic-only application-identity bridge tests; never FDA decisions."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path

import pytest

from app.hop_fda_original_letter_bridge import (
    STATES, crosswalk_original_submissions_to_published_letters,
)

CUTOFF = date(2026, 10, 25)


def spine():
    rows = [
        ("NDA000001", "NDA", 1),
        ("NDA000001", "NDA", 2),
        ("BLA000002", "BLA", 1),
    ]
    return {
        "status": "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY",
        "source_application_tsv_sha256": "a" * 64,
        "source_submission_tsv_sha256": "b" * 64,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "complete_original_nda_bla_application_denominator_verified": False,
        "independently_verified_fda_review_cycles": 0,
        "submission_number_is_not_review_cycle": True,
        "raw_status_not_a_verified_decision_label": True,
        "original_nda_bla_submission_rows": 3,
        "distinct_nda_bla_applications_in_original_submission_inventory": 2,
        "candidate_original_submissions": [{
            "application_id": app,
            "application_type": category,
            "submission_kind": "ORIG",
            "original_submission_number": number,
            "independently_verified": False,
            "model_eligible": False,
            "review_cycle": None,
            "fda_action_outcome": None,
        } for app, category, number in rows],
    }


def letter(idx, apps, typ="COMPLETE RESPONSE"):
    return {
        "source_record_sha256": f"{idx:064x}",
        "application_numbers": apps,
        "letter_type_as_published": typ,
        "independently_verified": False,
        "cohort_complete_verified": False,
        "model_eligible": False,
        "review_cycle": None,
    }


def letters(*values):
    return {
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "source_export_date": "2026-10-21",
        "records": list(values),
    }


def report(s=None, l=None):
    return crosswalk_original_submissions_to_published_letters(
        s or spine(), l or letters(letter(1, ["NDA 000001"])), as_of=CUTOFF,
    )


def test_identity_link_states_partition_every_published_letter_without_model():
    output = report(l=letters(
        letter(1, ["NDA 000001/Original 2"]),
        letter(2, ["NDA 000001"]),
        letter(3, ["BLA 000002"]),
        letter(4, ["NDA 999999"]),
        letter(5, ["ANDA 123456"]),
        letter(6, ["BL 125845"]),
        letter(7, ["NDA 000001", "BLA 000002"]),
        letter(8, ["NDA 000001", "UNKNOWN"]),
    ))
    assert output["published_letter_references"] == 8
    assert output["published_letter_reference_link_states"] == {
        "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE": 3,
        "NDA_BLA_APPLICATION_NOT_IN_ORIGINAL_SUBMISSION_SPINE": 1,
        "ANDA_OUT_OF_STUDY_SCOPE": 1,
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION": 3,
    }
    assert set(output["published_letter_reference_link_states"]) == set(STATES)
    assert output["distinct_original_spine_applications_referenced_by_published_letters"] == 2
    assert output["matched_original_spine_applications_with_repeated_letter_references"] == 1
    assert output["matched_letter_references_with_multiple_original_submission_numbers"] == 2
    assert output["textual_original_qualifier_comparison_counts"] == {
        "ORIGINAL_QUALIFIER_MATCHES_SUBMISSION_NUMBER_TEXT_ONLY": 1,
    }
    assert output["independently_verified_fda_review_cycles"] == 0
    assert output["complete_nda_bla_decision_denominator_verified"] is False
    assert output["approval_rate"] is None
    assert output["prediction_probability"] is None
    assert output["prediction_accuracy"] is None
    assert output["model_eligible_records"] == 0


def test_qualified_original_serial_missing_from_source_is_only_a_review_flag():
    out = report(l=letters(letter(1, ["NDA 000001/Original 10"])))
    assert out["textual_original_qualifier_comparison_counts"] == {
        "ORIGINAL_QUALIFIER_NOT_IN_SPINE_REQUIRES_REVIEW": 1
    }
    assert out["application_link_does_not_establish_same_review_cycle"] is True
    assert out["model_eligible_records"] == 0


def test_exact_match_never_claims_approval_or_decision_denominator():
    out = report()
    assert out["published_letter_reference_link_states"][
        "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE"
    ] == 1
    assert out["complete_nda_bla_decision_denominator_verified"] is False
    assert out["original_drugsfda_source_approval_centric"] is True
    assert out["published_crl_corpus_selectively_released"] is True
    assert out["unmatched_record_does_not_prove_never_approved"] is True


@pytest.mark.parametrize("change", [
    "original_outcome", "original_cycle", "original_promoted",
    "original_count", "original_duplicate", "original_type", "original_denominator",
    "letter_promoted", "letter_cycle", "duplicate_letter", "future_export",
])
def test_rejects_promoted_deduplicated_or_invalid_source_claims(change):
    s = spine()
    l = letters(letter(1, ["NDA 000001"]))
    if change == "original_outcome":
        s["candidate_original_submissions"][0]["fda_action_outcome"] = "APPROVED"
    elif change == "original_cycle":
        s["candidate_original_submissions"][0]["review_cycle"] = 2
    elif change == "original_promoted":
        s["candidate_original_submissions"][0]["model_eligible"] = True
    elif change == "original_count":
        s["original_nda_bla_submission_rows"] = 4
    elif change == "original_duplicate":
        s["candidate_original_submissions"][1]["original_submission_number"] = 1
    elif change == "original_type":
        s["candidate_original_submissions"][0]["application_type"] = "BLA"
    elif change == "original_denominator":
        s["complete_original_nda_bla_application_denominator_verified"] = True
    elif change == "letter_promoted":
        l["records"][0]["model_eligible"] = True
    elif change == "letter_cycle":
        l["records"][0]["review_cycle"] = 1
    elif change == "duplicate_letter":
        l["records"].append(deepcopy(l["records"][0]))
    elif change == "future_export":
        l["source_export_date"] = "2027-01-01"
    with pytest.raises(ValueError):
        crosswalk_original_submissions_to_published_letters(s, l, as_of=CUTOFF)


def test_empty_crl_rejected_not_misread_as_fda_no_actions():
    with pytest.raises(ValueError):
        report(l=letters())


def test_mixed_supplement_and_original_same_application_just_identity_match():
    out = report(l=letters(letter(1, [
        "NDA 000001/S-001", "NDA 000001/Original 2"
    ])))
    assert out["published_letter_reference_link_states"][
        "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE"
    ] == 1
    assert out["textual_original_qualifier_comparison_counts"][
        "ORIGINAL_QUALIFIER_MATCHES_SUBMISSION_NUMBER_TEXT_ONLY"
    ] == 1
    assert out["independently_verified_fda_review_cycles"] == 0



def test_actual_october_25_identity_link_baseline_has_no_model_clearance():
    path = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
            / "hop_fda_original_letter_bridge_20261025.json")
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["status"] == "NDA_BLA_ORIGINAL_SUBMISSION_LETTER_IDENTITY_CROSSWALK_ONLY"
    assert report["published_letter_references"] == 458
    assert report["original_nda_bla_submission_history_rows"] == 6033
    assert report["distinct_nda_bla_applications_in_approval_centric_spine"] == 5973
    assert report["published_letter_reference_link_states"] == {
        "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE": 334,
        "NDA_BLA_APPLICATION_NOT_IN_ORIGINAL_SUBMISSION_SPINE": 107,
        "ANDA_OUT_OF_STUDY_SCOPE": 0,
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION": 17,
    }
    assert sum(report["published_letter_reference_link_states"].values()) == 458
    assert report["distinct_original_spine_applications_referenced_by_published_letters"] == 238
    assert report["matched_original_spine_applications_with_repeated_letter_references"] == 63
    assert report["matched_letter_references_with_multiple_original_submission_numbers"] == 11
    assert report["textual_original_qualifier_comparison_counts"] == {
        "ORIGINAL_QUALIFIER_MATCHES_SUBMISSION_NUMBER_TEXT_ONLY": 7,
        "ORIGINAL_QUALIFIER_NOT_IN_SPINE_REQUIRES_REVIEW": 3,
    }
    assert report["run_url"].endswith("/40247135687")
    assert len(report["source_crl_archive_sha256"]) == 64
    assert report["application_link_does_not_establish_same_review_cycle"] is True
    assert report["unmatched_record_does_not_prove_never_approved"] is True
    assert report["independently_verified_fda_review_cycles"] == 0
    assert report["complete_nda_bla_decision_denominator_verified"] is False
    assert report["model_eligible_records"] == 0
    assert report["approval_rate"] is None
    assert report["prediction_probability"] is None
    assert report["prediction_accuracy"] is None
