"""Strict synthetic tests for a non-predictive FDA letter-source gap review queue."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import hashlib

import pytest

from app.hop_fda_unmatched_letter_triage import build_letter_identity_gap_triage

CUTOFF = date(2026, 10, 25)
APPLICATIONS = ("ApplNo\tApplType\tSponsorName\n"
                "000001\tNDA\tSynthetic\n"
                "000002\tBLA\tSynthetic\n"
                "000003\tNDA\tSynthetic\n"
                "000004\tNDA\tSynthetic\n"
                "000005\tANDA\tSynthetic\n")


def fixtures(tmp_path):
    path = tmp_path / "Applications.txt"
    path.write_text(APPLICATIONS, encoding="utf-8")
    spine = {
        "status": "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY",
        "research_cutoff": "2026-10-25",
        "source_application_tsv_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "source_submission_tsv_sha256": "b" * 64,
        "application_rows_in_extract": 5,
        "validated_application_identity_rows": 5,
        "quarantined_application_row_reason_counts": {},
        "model_eligible_records": 0,
        "prediction_probability": None,
        "complete_original_nda_bla_application_denominator_verified": False,
        "independently_verified_fda_review_cycles": 0,
        "submission_number_is_not_review_cycle": True,
        "raw_status_not_a_verified_decision_label": True,
        "original_nda_bla_submission_rows": 2,
        "distinct_nda_bla_applications_in_original_submission_inventory": 2,
        "candidate_original_submissions": [
            {
                "application_id": app, "application_type": app[:3],
                "submission_kind": "ORIG", "original_submission_number": 1,
                "review_cycle": None, "fda_action_outcome": None,
                "independently_verified": False, "model_eligible": False,
            } for app in ("NDA000001", "BLA000002")
        ],
    }

    def letter(i, apps, typ="COMPLETE RESPONSE"):
        return {
            "source_record_sha256": f"{i:064x}", "application_numbers": apps,
            "letter_type_as_published": typ, "letter_date_as_published": "2020-01-01",
            "model_eligible": False, "independently_verified": False,
            "cohort_complete_verified": False, "review_cycle": None,
        }

    letters = {
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "source_export_date": "2026-10-21",
        "retrieved_on": "2026-10-25",
        "records": [
            letter(1, ["NDA 000001"]),
            letter(2, ["BLA 000002"]),
            letter(3, ["NDA 000003"]),
            letter(4, ["NDA 000003/Original 2"]),
            letter(5, ["NDA 999999"]),
            letter(6, ["BL 125845"]),
            letter(7, ["NDA 000001", "BLA 000002"]),
            letter(8, ["ANDA 000005"], typ="TENTATIVE APPROVAL"),
        ],
    }
    return path, spine, letters


def run(*parts):
    path, spine, letters = parts
    return build_letter_identity_gap_triage(
        spine, letters, applications_tsv=path, as_of=CUTOFF
    )


def test_classifies_qualified_app_roster_gap_vs_not_in_fda_roster(tmp_path):
    queue, audit = run(*fixtures(tmp_path))
    assert audit["published_letter_references"] == 8
    assert audit["matched_original_application_letter_references"] == 2
    assert audit["nda_bla_no_original_spine_letter_references"] == 3
    assert audit["ambiguous_or_unparseable_letter_references"] == 2
    assert audit["anda_out_of_scope_letter_references"] == 1
    assert audit["review_queue_references"] == 5
    assert audit["review_queue_reasons"] == {
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION": 2,
        "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION": 2,
        "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE": 1,
    }
    assert audit["distinct_candidate_applications_needing_source_research"] == 2
    assert audit["candidate_applications_with_repeated_published_letters"] == 1
    assert audit["maximum_published_letter_references_for_one_missing_application"] == 2
    assert [x["review_priority"] for x in queue] == ["1", "1", "2", "2", "3"]
    assert {x["application_candidate"] for x in queue if x["review_priority"] == "2"} == {
        "NDA000003"
    }
    assert all(x["original_application_review_cycle"] is None for x in queue)
    assert all(x["evidence_independently_adjudicated"] is False
               and x["model_eligible"] is False and x["fda_action_outcome"] is None
               for x in queue)
    assert audit["fda_original_actions_independently_verified"] == 0
    assert audit["complete_original_nda_bla_decision_denominator_verified"] is False
    assert audit["prediction_probability"] is None


def test_repeated_missing_app_references_are_not_additional_decisions(tmp_path):
    queue, audit = run(*fixtures(tmp_path))
    repeated = [x for x in queue if x["application_candidate"] == "NDA000003"]
    assert len(repeated) == 2
    assert all(x["repeated_published_letter_references_for_candidate"] == 2
               for x in repeated)
    assert all(x["review_task"] ==
               "CHECK_ORIGINAL_SUBMISSION_HISTORY_AND_INDEPENDENT_FDA_ACTIONS"
               for x in repeated)
    assert audit["model_eligible_records"] == 0


@pytest.mark.parametrize("modification", [
    "tampered_application_source",
    "future_letter",
    "promoted_original",
    "promoted_letter",
    "duplicate_letter",
    "missing_application_column",
    "unexpected_count",
    "missing_source_record",
    "invalid_letter_type",
])
def test_tampered_source_data_fails_closed(tmp_path, modification):
    path, spine, letters = fixtures(tmp_path)
    if modification == "tampered_application_source":
        path.write_text(APPLICATIONS.replace("000003", "000006"), encoding="utf-8")
    elif modification == "future_letter":
        letters["source_export_date"] = "2027-01-01"
    elif modification == "promoted_original":
        spine["candidate_original_submissions"][0]["review_cycle"] = 1
    elif modification == "promoted_letter":
        letters["records"][2]["model_eligible"] = True
    elif modification == "duplicate_letter":
        letters["records"].append(deepcopy(letters["records"][2]))
    elif modification == "missing_application_column":
        path.write_text("ApplNo\n000001\n", encoding="utf-8")
        spine["source_application_tsv_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif modification == "unexpected_count":
        spine["validated_application_identity_rows"] = 4
    elif modification == "missing_source_record":
        spine["original_nda_bla_submission_rows"] = 1
    elif modification == "invalid_letter_type":
        letters["records"][3]["letter_type_as_published"] = "=IMPORTXML(1)"
    with pytest.raises(ValueError):
        run(path, spine, letters)


def test_other_valid_tabular_application_but_missing_orig_is_not_a_denial(tmp_path):
    path, spine, letters = fixtures(tmp_path)
    letters["records"] = [letters["records"][2]]
    queue, audit = run(path, spine, letters)
    assert queue[0]["review_reason"] == "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION"
    assert queue[0]["fda_action_outcome"] is None
    assert audit["nonmatch_does_not_prove_never_approved"] is True


def test_empty_published_letters_do_not_establish_approval_cohort(tmp_path):
    path, spine, letters = fixtures(tmp_path)
    letters["records"] = []
    with pytest.raises(ValueError):
        run(path, spine, letters)



def test_real_pinned_unmatched_letter_review_population_is_consistent():
    """Real FDA count snapshot, no original-action labels or FDA probabilities."""
    import json
    source_dir = Path(__file__).resolve().parents[1] / "app" / "research_sources"
    audit = json.loads(
        (source_dir / "hop_fda_unmatched_letter_gap_audit_20261025.json")
        .read_text(encoding="utf-8")
    )
    bridge = json.loads(
        (source_dir / "hop_fda_original_letter_bridge_20261025.json")
        .read_text(encoding="utf-8")
    )
    original = json.loads(
        (source_dir / "hop_drugsfda_original_submissions_20261025.json")
        .read_text(encoding="utf-8")
    )
    assert audit["published_letter_references"] == bridge["published_letter_references"] == 458
    assert audit["source_applications_tsv_sha256"] == original["applications_tsv_sha256"]
    assert audit["source_submissions_tsv_sha256"] == original["submissions_tsv_sha256"]
    assert audit["matched_original_application_letter_references"] == 334
    assert bridge["published_letter_reference_link_states"][
        "NDA_BLA_APPLICATION_IN_ORIGINAL_SUBMISSION_SPINE"
    ] == 334
    assert audit["nda_bla_no_original_spine_letter_references"] == 107
    assert bridge["published_letter_reference_link_states"][
        "NDA_BLA_APPLICATION_NOT_IN_ORIGINAL_SUBMISSION_SPINE"
    ] == 107
    assert audit["ambiguous_or_unparseable_letter_references"] == 17
    assert bridge["published_letter_reference_link_states"][
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION"
    ] == 17
    assert audit["review_queue_references"] == 124
    assert audit["review_queue_reasons"] == {
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION": 17,
        "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION": 0,
        "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE": 107,
    }
    assert audit["distinct_candidate_applications_needing_source_research"] == 84
    assert audit["candidate_applications_with_repeated_published_letters"] == 20
    assert audit["maximum_published_letter_references_for_one_missing_application"] == 3
    assert audit["private_letter_level_queue_not_exported"] is True
    assert audit["fda_original_actions_independently_verified"] == 0
    assert audit["complete_original_nda_bla_decision_denominator_verified"] is False
    assert audit["model_eligible_records"] == 0
    assert audit["approval_rate"] is None
    assert audit["prediction_probability"] is None
    assert audit["predictive_accuracy"] is None
