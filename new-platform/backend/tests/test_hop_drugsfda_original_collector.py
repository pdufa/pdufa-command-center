"""No network access: synthetic ZIP fixtures test the official FDA collector."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import date

import pytest

from scripts.collect_hop_drugsfda_original_submissions import (
    OFFICIAL_DOWNLOAD, _official_final_url, collect_aggregate_audit,
    download_official_source_bytes, extract_two_official_tables,
)

AS_OF = date(2026, 10, 25)
APPS = (
    "ApplNo\tApplType\tSponsorName\n"
    "123456\tNDA\tFictional sponsor\n"
    "654321\tBLA\tFictional sponsor\n"
    "111111\tANDA\tFictional sponsor\n"
)
SUBMISSIONS = (
    "ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\t"
    "SubmissionStatusDate\n"
    "123456\tORIG\t1\tAP\t2020-01-01\n"
    "123456\tSUPPL\t2\tAP\t2020-01-02\n"
    "654321\tORIG\t1\tCR\t2020-01-03\n"
    "111111\tORIG\t1\tAP\t2020-01-04\n"
)


def archive(apps=APPS, subs=SUBMISSIONS, extra=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr("snapshot/Applications.txt", apps)
        zipf.writestr("snapshot/Submissions.txt", subs)
        if extra:
            for name, content in extra.items():
                zipf.writestr(name, content)
    return buffer.getvalue()


def test_offline_collection_records_only_aggregate_unverified_counts(tmp_path):
    doc = archive()
    result = collect_aggregate_audit(
        doc, "https://www.fda.gov/media/89850/download?attachment=",
        tmp_path / "work", as_of=AS_OF,
    )
    assert result["source_zip_sha256"]
    assert result["applications_tsv_sha256"]
    assert result["submissions_tsv_sha256"]
    assert result["application_rows_in_extract"] == 3
    assert result["submission_rows_in_extract"] == 4
    assert result["original_nda_bla_submission_rows"] == 2
    assert result["distinct_nda_bla_applications_in_original_submission_inventory"] == 2
    assert result["independently_verified_fda_review_cycles"] == 0
    assert result["model_eligible_records"] == 0
    assert result["complete_original_nda_bla_application_denominator_verified"] is False
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None
    assert result["predictive_accuracy"] is None
    assert result["no_training_or_production_import"] is True
    assert "candidate_original_submissions" not in result
    assert "raw_submission_status_code" not in json.dumps(result)
    assert "Fictional sponsor" not in json.dumps(result)


@pytest.mark.parametrize("name", [
    "../../Applications.txt", "/tmp/Applications.txt", "C:/bad/Applications.txt",
])
def test_zip_path_traversal_fails_closed(tmp_path, name):
    with pytest.raises(ValueError):
        extract_two_official_tables(
            archive(extra={name: "UNTRUSTED"}), tmp_path
        )


def test_rejects_duplicate_table_names_even_if_different_parent_path(tmp_path):
    with pytest.raises(ValueError):
        extract_two_official_tables(
            archive(extra={"elsewhere/applications.txt": APPS}), tmp_path,
        )


def test_rejects_missing_expected_table(tmp_path):
    contents = io.BytesIO()
    with zipfile.ZipFile(contents, "w") as zipf:
        zipf.writestr("Applications.txt", APPS)
    with pytest.raises(ValueError):
        extract_two_official_tables(contents.getvalue(), tmp_path)


def test_rejects_bad_zip_bytes(tmp_path):
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        extract_two_official_tables(b"not a ZIP" * 10, tmp_path)


@pytest.mark.parametrize("url", [
    "http://www.fda.gov/media/89850/download",
    "https://www.fda.gov.evil.example/media/89850/download",
    "https://evil.example/media/89850/download",
    "https://www.fda.gov@evil.example/media/89850/download",
    "https://www.fda.gov:444/media/89850/download",
])
def test_official_source_redirect_rejects_spoofed_urls(url):
    assert _official_final_url(url) is False


def test_no_arbitrary_source_urls_for_official_collect():
    with pytest.raises(ValueError):
        download_official_source_bytes(
            "https://www.fda.gov.evil.example/media/89850/download"
        )


def test_source_summary_rejects_external_redirect(tmp_path):
    with pytest.raises(ValueError):
        collect_aggregate_audit(
            archive(), "https://example.org/zip", tmp_path, as_of=AS_OF
        )


def test_pinned_official_fda_source_is_valid_https():
    assert _official_final_url(OFFICIAL_DOWNLOAD) is True
