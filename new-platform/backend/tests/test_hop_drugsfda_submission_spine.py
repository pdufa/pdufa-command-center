"""Tests use fictitious Drugs@FDA rows, not real FDA clinical outcomes."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.hop_drugsfda_submission_spine import audit_original_submissions

AS_OF = date(2026, 10, 25)
APP_HEADER = "ApplNo\tApplType\tSponsorName\n"
SUB_HEADER = ("ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\t"
              "SubmissionStatusDate\tSubmissionsPublicNotes\n")


def inputs(tmp_path, apps=None, subs=None):
    if apps is None:
        apps = [
            "123456\tNDA\tFictitious sponsor",
            "654321\tBLA\tFictitious sponsor",
            "112233\tANDA\tFictitious sponsor",
        ]
    if subs is None:
        subs = [
            "123456\tORIG\t1\tAP\t2020-01-01\tFAKE",
            "123456\tORIG\t2\tCR\t2020-01-03\tFAKE",
            "654321\tORIG\t1\tAP\t2020-02-01\tFAKE",
            "123456\tSUPPL\t3\tAP\t2020-04-01\tFAKE",
            "112233\tORIG\t1\tAP\t2020-05-01\tFAKE",
            "999999\tORIG\t1\tAP\t2020-06-01\tFAKE",
        ]
    ap, su = tmp_path / "Applications.txt", tmp_path / "Submissions.txt"
    ap.write_text(APP_HEADER + "\n".join(apps) + "\n", encoding="utf-8")
    su.write_text(SUB_HEADER + "\n".join(subs) + "\n", encoding="utf-8")
    return ap, su


def audit(tmp_path, apps=None, subs=None):
    ap, su = inputs(tmp_path, apps, subs)
    return audit_original_submissions(ap, su, as_of=AS_OF)


def test_only_original_nda_bla_submission_history_not_cycle_population(tmp_path):
    result = audit(tmp_path)
    assert result["application_rows_in_extract"] == 3
    assert result["submission_rows_in_extract"] == 6
    assert result["application_type_counts"] == {"ANDA": 1, "BLA": 1, "NDA": 1}
    assert result["original_nda_bla_submission_rows"] == 3
    assert result["distinct_nda_bla_applications_in_original_submission_inventory"] == 2
    assert result["excluded_submission_row_reason_counts"] == {
        "NON_NDA_BLA_APPLICATION": 1,
        "NOT_AN_ORIGINAL_SUBMISSION": 1,
        "NO_MATCHING_APPLICATION_ROW": 1,
    }
    assert {(r["application_id"], r["original_submission_number"]) for r in
            result["candidate_original_submissions"]} == {
                ("NDA123456", 1), ("NDA123456", 2), ("BLA654321", 1)
            }
    assert result["source_application_tsv_sha256"] != result["source_submission_tsv_sha256"]
    assert result["submission_number_is_not_review_cycle"] is True
    assert result["unapproved_applications_absent_from_export_possible"] is True
    assert result["independently_verified_fda_review_cycles"] == 0
    assert result["complete_original_nda_bla_application_denominator_verified"] is False
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None
    assert all(r["review_cycle"] is None and r["fda_action_outcome"] is None
               and r["model_eligible"] is False
               for r in result["candidate_original_submissions"])


def test_duplicate_submission_keys_never_count_as_new_regulatory_cycles(tmp_path):
    result = audit(tmp_path, subs=[
        "123456\tORIG\t1\tAP\t2020-01-01\tFAKE",
        "123456\tORIG\t01\tCR\t2020-01-02\tFAKE",
    ])
    assert result["submission_rows_in_extract"] == 2
    assert result["original_nda_bla_submission_rows"] == 1
    assert result["source_data_quality_flag_counts"] == {
        "DUPLICATE_SUBMISSION_KEY_REQUIRES_RECONCILIATION": 1,
    }
    assert result["independently_verified_fda_review_cycles"] == 0


def test_untrusted_status_and_missing_or_future_dates_are_quarantined(tmp_path):
    result = audit(tmp_path, subs=[
        "123456\tORIG\t1\t=HYPERLINK(1)\t2020-01-01\tFAKE",
        "123456\tORIG\t2\tAP\t\tFAKE",
        "123456\tORIG\t3\tAP\t2027-01-01\tFAKE",
        "654321\tORIG\t1\tCR\t2020-44-99\tFAKE",
    ])
    assert result["original_nda_bla_submission_rows"] == 4
    flags = result["source_data_quality_flag_counts"]
    assert flags["RAW_SUBMISSION_STATUS_UNPARSEABLE"] == 1
    assert flags["RAW_SUBMISSION_DATE_MISSING"] == 1
    assert flags["RAW_SUBMISSION_DATE_UNPARSEABLE"] == 1
    assert flags["RAW_SUBMISSION_DATE_AFTER_RESEARCH_CUTOFF"] == 1
    assert result["candidate_original_submissions"][0]["raw_submission_status_code"] == ""
    assert all(not item["model_eligible"] for item in result["candidate_original_submissions"])


def test_dates_are_metadata_not_independently_verified_outcomes(tmp_path):
    result = audit(tmp_path, subs=[
        "123456\tORIG\t1\tAP\t2020-01-01 00:00:00\tFAKE",
        "654321\tORIG\t1\tCR\t02/04/2020\tFAKE",
    ])
    assert {r["raw_submission_status_date"] for r in result["candidate_original_submissions"]} == {
        "2020-01-01", "2020-02-04"
    }
    assert result["model_eligible_records"] == 0
    assert result["raw_status_not_a_verified_decision_label"] is True


@pytest.mark.parametrize("change", [
    "bad_application_id", "duplicate_application", "missing_application_col",
    "bad_submission_id", "bad_submission_number", "extra_tab",
    "missing_submission_column",
])
def test_malformed_or_ambiguous_fda_table_data_rejected(tmp_path, change):
    app = ["123456\tNDA\tFictitious"]
    sub = ["123456\tORIG\t1\tAP\t2020-01-01\tFAKE"]
    if change == "bad_application_id":
        app[0] = "NDA123456\tNDA\tFictitious"
    elif change == "duplicate_application":
        app.append(app[0])
    elif change == "missing_application_col":
        ap, su = inputs(tmp_path, app, sub)
        ap.write_text("ApplNo\tSponsorName\n123456\tFictitious\n", encoding="utf-8")
    elif change == "bad_submission_id":
        sub[0] = "x23456\tORIG\t1\tAP\t2020-01-01\tFAKE"
    elif change == "bad_submission_number":
        sub[0] = "123456\tORIG\tno\tAP\t2020-01-01\tFAKE"
    elif change == "extra_tab":
        sub[0] += "\tEXTRA"
    elif change == "missing_submission_column":
        ap, su = inputs(tmp_path, app, sub)
        su.write_text("ApplNo\tSubmissionNo\n123456\t1\n", encoding="utf-8")
    if change not in {"missing_application_col", "missing_submission_column"}:
        ap, su = inputs(tmp_path, app, sub)
    with pytest.raises(ValueError):
        audit_original_submissions(ap, su, as_of=AS_OF)


def test_no_application_rows_fails_as_empty_not_as_complete_denominator(tmp_path):
    result = audit(tmp_path, apps=[], subs=[])
    assert result["original_nda_bla_submission_rows"] == 0
    assert result["independently_verified_fda_review_cycles"] == 0
    assert result["complete_original_nda_bla_application_denominator_verified"] is False
    assert result["approval_rate"] is None


def test_explicit_cutoff_is_required(tmp_path):
    ap, su = inputs(tmp_path)
    with pytest.raises(ValueError):
        audit_original_submissions(ap, su, as_of=None)
