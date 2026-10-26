"""Synthetic source membership reconciliation, never FDA clinical outcome tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.hop_drugsfda_original_source_diff import reconcile_original_submission_sources

AS_OF = date(2026, 10, 25)
SHA_A, SHA_B, SHA_C = "a" * 64, "b" * 64, "c" * 64


def tabrow(app, n, status="AP", day="2020-01-01"):
    return {
        "application_id": app, "application_type": app[:3],
        "submission_kind": "ORIG", "original_submission_number": n,
        "raw_submission_status_code": status,
        "raw_submission_status_date": day,
        "review_cycle": None, "fda_action_outcome": None,
        "independently_verified": False, "model_eligible": False,
    }


def archived(app, number, status="AP", day="20200101"):
    return {
        "application_number_as_published": app,
        "model_eligible": False,
        "point_in_time_features_verified": False,
        "complete_application_denominator_verified": False,
        "review_cycles_independently_adjudicated": False,
        "submissions_as_published": [{
            "submission_type_as_published": "ORIG",
            "submission_number_as_published": str(number),
            "submission_status_as_published": status,
            "submission_status_date_as_published": day,
        }],
    }


def fixture():
    rows = [tabrow("NDA000001", 1), tabrow("BLA000002", 1)]
    tabular = {
        "status": "DRUGSFDA_ORIGINAL_SUBMISSION_SPINE_RESEARCH_ONLY",
        "research_cutoff": "2026-10-25",
        "source_application_tsv_sha256": SHA_A,
        "source_submission_tsv_sha256": SHA_B,
        "candidate_original_submissions": rows,
        "distinct_nda_bla_applications_in_original_submission_inventory": 2,
        "independently_verified_fda_review_cycles": 0,
        "complete_original_nda_bla_application_denominator_verified": False,
        "model_eligible_records": 0, "prediction_probability": None,
    }
    archive = {
        "schema_version": 1,
        "status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
        "records": [archived("NDA000001", 1),
                    archived("NDA000003", 1, status="TA")],
    }
    tab_index = {
        "status": "OFFICIAL_FDA_TABLE_ORIGINAL_SUBMISSIONS_QUARANTINED",
        "applications_tsv_sha256": SHA_A, "submissions_tsv_sha256": SHA_B,
        "original_nda_bla_submission_rows": 2,
        "distinct_nda_bla_applications_in_original_submission_inventory": 2,
        "model_eligible_records": 0, "prediction_probability": None,
    }
    archive_index = {
        "status": "ACTUAL_FDA_APPROVED_REGISTRY_ORIGINAL_SPINE_QUARANTINED",
        "github_artifact_json_sha256": SHA_C,
        "research_cutoff": "2026-10-25",
        "approved_registry_application_records": 2,
        "original_nda_bla_submission_entries": 2,
        "distinct_nda_bla_applications_with_original_submission": 2,
        "model_eligible_records": 0, "prediction_probability": None,
        "complete_original_nda_bla_denominator_verified": False,
    }
    return tabular, archive, tab_index, archive_index


def reconcile(*parts):
    return reconcile_original_submission_sources(
        *parts[:2], tabular_index=parts[2], archive_index=parts[3], as_of=AS_OF
    )


def test_real_source_keys_diff_without_inventing_fda_decisions():
    r = reconcile(*fixture())
    assert r["status"] == "ORIGINAL_SUBMISSION_SOURCE_MEMBERSHIP_RECONCILED_NOT_FDA_DECISIONS"
    assert r["shared_original_submission_keys"] == 1
    assert r["tabular_keys_absent_from_openfda"] == 1
    assert r["openfda_keys_absent_from_tabular"] == 1
    assert r["net_tabular_minus_openfda_original_keys"] == 0
    assert r["tabular_only_key_examples"] == [
        {"application_id": "BLA000002", "original_submission_number": 1}
    ]
    assert r["openfda_only_key_examples"] == [
        {"application_id": "NDA000003", "original_submission_number": 1}
    ]
    assert r["shared_keys_with_raw_status_mismatch"] == 0
    assert r["complete_fda_decision_denominator_verified"] is False
    assert r["model_eligible_records"] == 0
    assert r["prediction_probability"] is None
    assert r["predictive_accuracy"] is None


def test_matching_identity_may_have_different_raw_dates_or_codes():
    data = fixture()
    data[1]["records"][0]["submissions_as_published"][0].update({
        "submission_status_as_published": "CR",
        "submission_status_date_as_published": "20200102",
    })
    r = reconcile(*data)
    assert r["shared_keys_with_raw_status_mismatch"] == 1
    assert r["shared_keys_with_raw_status_date_mismatch"] == 1
    assert r["review_cycles_independently_verified"] == 0


def test_matching_all_still_never_validates_an_outcome():
    tab, arc, ti, ai = fixture()
    arc["records"] = [
        archived("NDA000001", 1),
        archived("BLA000002", 1),
    ]
    r = reconcile(tab, arc, ti, ai)
    assert r["tabular_keys_absent_from_openfda"] == 0
    assert r["openfda_keys_absent_from_tabular"] == 0
    assert r["complete_fda_decision_denominator_verified"] is False
    assert r["approval_rate"] is None


@pytest.mark.parametrize("kind", [
    "tabular_training", "archive_training", "bad_tabular_sha",
    "bad_archive_json_sha", "alter_tabular_counts",
    "alter_archive_counts", "unverified_review_claim", "duplicate_tabular_key",
    "duplicate_archived_key", "future_research_cutoff",
])
def test_tampering_and_model_promotion_are_blocked(kind):
    d = fixture()
    if kind == "tabular_training":
        d[0]["model_eligible_records"] = 1
    elif kind == "archive_training":
        d[1]["records"][0]["model_eligible"] = True
    elif kind == "bad_tabular_sha":
        d[2]["submissions_tsv_sha256"] = SHA_C
    elif kind == "bad_archive_json_sha":
        d[3]["github_artifact_json_sha256"] = "not_a_hash"
    elif kind == "alter_tabular_counts":
        d[2]["original_nda_bla_submission_rows"] = 10
    elif kind == "alter_archive_counts":
        d[3]["original_nda_bla_submission_entries"] = 999
    elif kind == "unverified_review_claim":
        d[0]["candidate_original_submissions"][0]["review_cycle"] = 1
    elif kind == "duplicate_tabular_key":
        d[0]["candidate_original_submissions"][1] = deepcopy(
            d[0]["candidate_original_submissions"][0]
        )
    elif kind == "duplicate_archived_key":
        d[1]["records"].append(deepcopy(d[1]["records"][0]))
        d[3]["approved_registry_application_records"] = 3
    elif kind == "future_research_cutoff":
        d[0]["research_cutoff"] = "2027-01-01"
    with pytest.raises(ValueError):
        reconcile(*d)


def test_bounded_sample_does_not_alter_full_membership_totals():
    tab, arc, ti, ai = fixture()
    r = reconcile_original_submission_sources(
        tab, arc, tabular_index=ti, archive_index=ai,
        as_of=AS_OF, max_examples=1
    )
    assert r["tabular_keys_absent_from_openfda"] == 1
    assert r["examples_truncated"] is False
    with pytest.raises(ValueError):
        reconcile_original_submission_sources(
            tab, arc, tabular_index=ti, archive_index=ai,
            as_of=AS_OF, max_examples=0,
        )



def test_actual_pinned_source_diff_proves_only_one_membership_exception():
    """Frozen run result is a source-identity finding, NOT an FDA outcome."""
    import json
    from pathlib import Path

    source_dir = Path(__file__).resolve().parents[1] / "app" / "research_sources"
    report = json.loads(
        (source_dir / "hop_drugsfda_original_source_diff_20261025.json")
        .read_text(encoding="utf-8")
    )
    table = json.loads(
        (source_dir / "hop_drugsfda_original_submissions_20261025.json")
        .read_text(encoding="utf-8")
    )
    archived = json.loads(
        (source_dir / "hop_drugsfda_original_submissions_artifact_index.json")
        .read_text(encoding="utf-8")
    )
    assert report["status"] == (
        "ORIGINAL_SUBMISSION_SOURCE_MEMBERSHIP_RECONCILED_NOT_FDA_DECISIONS"
    )
    assert report["tabular_original_submission_keys"] == (
        table["original_nda_bla_submission_rows"] == 6033
    )
    assert report["openfda_archived_original_submission_keys"] == (
        archived["original_nda_bla_submission_entries"] == 6032
    )
    assert report["source_versions"]["tabular_applications_tsv_sha256"] == (
        table["applications_tsv_sha256"]
    )
    assert report["source_versions"]["tabular_submissions_tsv_sha256"] == (
        table["submissions_tsv_sha256"]
    )
    assert report["source_versions"]["openfda_approved_registry_artifact_json_sha256"] == (
        archived["github_artifact_json_sha256"]
    )
    assert report["tabular_only_key_examples"] == [
        {"application_id": "NDA206627", "original_submission_number": 1}
    ]
    assert report["tabular_keys_absent_from_openfda"] == 1
    assert report["openfda_keys_absent_from_tabular"] == 0
    assert report["shared_original_submission_keys"] == 6032
    assert report["shared_keys_with_raw_status_mismatch"] == 0
    assert report["shared_keys_with_raw_status_date_mismatch"] == 0
    assert report["net_tabular_minus_openfda_original_keys"] == 1
    assert report["examples_truncated"] is False
    assert report["original_fda_action_dates_independently_verified"] == 0
    assert report["review_cycles_independently_verified"] == 0
    assert report["complete_fda_decision_denominator_verified"] is False
    assert report["model_eligible_records"] == 0
    assert report["prediction_probability"] is None
    assert report["predictive_accuracy"] is None
    assert report["readiness"] == "REVIEW_REQUIRED"
