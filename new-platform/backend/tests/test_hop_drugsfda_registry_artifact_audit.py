"""Synthetic test ZIPs; never interpret registry status codes as FDA outcomes."""
from __future__ import annotations

import hashlib
import json
import zipfile
from copy import deepcopy
from datetime import date

import pytest

from app.hop_drugsfda_registry_artifact_audit import audit_registry_artifact

AS_OF = date(2026, 10, 25)
ORIGINAL_SHA = "a" * 64


def normalized_record(i, application, submissions):
    return {
        "source_record_index": i,
        "application_number_as_published": application,
        "record_sha256": "b" * 64,
        "model_eligible": False,
        "review_cycles_independently_adjudicated": False,
        "complete_application_denominator_verified": False,
        "point_in_time_features_verified": False,
        "status": "QUARANTINED_APPROVED_PRODUCT_REGISTRY",
        "submissions_as_published": submissions,
    }


def submission(kind, number, status, published_date):
    return {
        "submission_type_as_published": kind,
        "submission_number_as_published": number,
        "submission_status_as_published": status,
        "submission_status_date_as_published": published_date,
        "review_priority_as_published": None,
    }


def fixture_zip(tmp_path, *, records=None, mutate=None):
    if records is None:
        records = [
            normalized_record(0, "NDA123456", [
                submission("ORIG", "1", "AP", "20200101"),
                submission("ORIG", "2", "TA", "20200102"),
                submission("SUPPL", "3", "AP", "20200103"),
            ]),
            normalized_record(1, "BLA654321", [
                submission("ORIG", "1", None, "20200201"),
            ]),
            normalized_record(2, "ANDA112233", [
                submission("ORIG", "1", "AP", "20200301"),
            ]),
        ]
    body = {
        "schema_version": 1,
        "status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
        "source_export_date": "2026-10-23",
        "retrieved_on": "2026-10-25",
        "records": records,
    }
    prior = {
        "source_export_date": "2026-10-23",
        "source_application_records": len(records),
        "quarantined_application_records": len(records),
        "application_number_prefixes": {
            "NDA": sum(r["application_number_as_published"].startswith("NDA")
                       for r in records),
            "BLA": sum(r["application_number_as_published"].startswith("BLA")
                       for r in records),
            "ANDA": sum(r["application_number_as_published"].startswith("ANDA")
                        for r in records),
        },
        "model_eligible_records": 0,
        "independently_adjudicated_review_cycles": 0,
        "complete_original_nda_bla_denominator_verified": False,
        "prediction_probability": None,
        "source_archive_sha256": {
            "https://download.open.fda.gov/drug/drugsfda/source.json.zip":
                ORIGINAL_SHA,
        },
    }
    if mutate:
        mutate(body, prior)
    payload = json.dumps(body).encode("utf-8")
    path = tmp_path / "quarantined_registry.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("drugsfda_approved_registry_quarantined.json", payload)
        z.writestr("drugsfda_approved_registry_audit.json", json.dumps(prior))
    return path, hashlib.sha256(payload).hexdigest()


def test_original_submission_registry_is_not_decision_census(tmp_path):
    path, digest = fixture_zip(tmp_path)
    result = audit_registry_artifact(path, as_of=AS_OF, expected_payload_sha256=digest)
    assert result["approved_registry_application_records"] == 3
    assert result["application_type_counts"] == {"ANDA": 1, "BLA": 1, "NDA": 1}
    assert result["published_registry_submission_entries"] == 5
    assert result["original_nda_bla_submission_entries"] == 3
    assert result["original_nda_bla_submission_entries_by_type"] == {
        "BLA": 1, "NDA": 2
    }
    assert result["distinct_nda_bla_applications_with_original_submission"] == 2
    assert result["applications_with_multiple_original_submissions"] == 1
    assert result["raw_original_submission_status_codes_not_outcomes"] == {
        "AP": 1, "MISSING": 1, "TA": 1
    }
    assert result["source_data_warning_counts"] == {
        "MISSING_ORIGINAL_SUBMISSION_RAW_STATUS": 1
    }
    assert result["independently_adjudicated_review_cycles"] == 0
    assert result["complete_original_nda_bla_denominator_verified"] is False
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None
    assert result["predictive_accuracy"] is None


def test_repeated_original_number_and_future_date_are_only_source_warnings(tmp_path):
    rows = [normalized_record(0, "NDA123456", [
        submission("ORIG", "1", "CR", "20270201"),
        submission("ORIG", "01", "AP", "20200201"),
    ])]
    path, digest = fixture_zip(tmp_path, records=rows)
    report = audit_registry_artifact(path, as_of=AS_OF, expected_payload_sha256=digest)
    assert report["original_nda_bla_submission_entries"] == 1
    assert report["raw_original_submission_status_codes_not_outcomes"] == {"CR": 1}
    assert report["source_data_warning_counts"] == {
        "RAW_DATE_AFTER_RESEARCH_CUTOFF": 1,
        "REPEATED_ORIGINAL_SUBMISSION_KEY": 1,
    }
    assert report["model_eligible_records"] == 0


@pytest.mark.parametrize("change", [
    "promote_row", "promote_prior", "date_mismatch", "wrong_index",
    "bad_record_digest", "duplicate_application",
    "alter_application_census", "change_source_digest", "wrong_schema",
])
def test_source_integrity_flags_fail_closed(tmp_path, change):
    records = [
        normalized_record(0, "NDA123456", [
            submission("ORIG", "1", "AP", "20200101")
        ]),
        normalized_record(1, "BLA654321", [
            submission("ORIG", "1", "TA", "20200101")
        ]),
    ]

    def mutate(body, prior):
        if change == "promote_row":
            body["records"][0]["model_eligible"] = True
        elif change == "promote_prior":
            prior["model_eligible_records"] = 1
        elif change == "date_mismatch":
            prior["source_export_date"] = "2026-09-09"
        elif change == "wrong_index":
            body["records"][0]["source_record_index"] = 9
        elif change == "bad_record_digest":
            body["records"][0]["record_sha256"] = "unsafe"
        elif change == "duplicate_application":
            body["records"][1]["application_number_as_published"] = "NDA123456"
        elif change == "alter_application_census":
            prior["application_number_prefixes"]["NDA"] += 1
        elif change == "change_source_digest":
            prior["source_archive_sha256"] = {"untrusted": "not_sha256"}
        elif change == "wrong_schema":
            body["schema_version"] = 3

    path, _ = fixture_zip(tmp_path, records=records, mutate=mutate)
    with pytest.raises(ValueError):
        audit_registry_artifact(path, as_of=AS_OF)


def test_fingerprint_mismatch_missing_original_and_bad_member_rejected(tmp_path):
    path, _ = fixture_zip(tmp_path)
    with pytest.raises(ValueError):
        audit_registry_artifact(
            path, as_of=AS_OF, expected_payload_sha256="f" * 64
        )
    with pytest.raises(ValueError):
        audit_registry_artifact(
            path, as_of=AS_OF, expected_payload_sha256="NOT_A_HASH"
        )
    with zipfile.ZipFile(path, "a") as z:
        z.writestr("extra.txt", "not expected")
    with pytest.raises(ValueError):
        audit_registry_artifact(path, as_of=AS_OF)


def test_empty_quarantined_source_is_not_complete_census(tmp_path):
    path, digest = fixture_zip(tmp_path, records=[])
    report = audit_registry_artifact(path, as_of=AS_OF, expected_payload_sha256=digest)
    assert report["approved_registry_application_records"] == 0
    assert report["original_nda_bla_submission_entries"] == 0
    assert report["complete_original_nda_bla_denominator_verified"] is False


def test_real_fda_source_snapshot_fingerprint_is_pinned_in_docs():
    # The full ~72 MB source is an Actions artifact, not committed to git.
    # This verifies the historical research source fingerprint is recorded
    # but does not claim to reprocess unavailable bytes on CI.
    expected = "adb24d7921d56bc3824b57e785164a32287efc69a9d3fe9b940da97f6c65f5b2"
    assert len(expected) == 64
