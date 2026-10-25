import io
import json
import zipfile
from datetime import date

import pytest

from app.hop_openfda_snapshot import build_crl_snapshot

URL = "https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip"


def make_archive(rows):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("transparency-crl.json", json.dumps({"results": rows}))
    return stream.getvalue()


def metadata(n=2, url=URL):
    return {"results": {"transparency": {"crl": {
        "export_date": "2026-10-21",
        "total_records": n,
        "partitions": [{"file": url, "records": n}],
    }}}}


def sample_rows():
    return [
        {"application_number": ["NDA 209510"], "letter_date": "10/05/2018",
         "letter_type": "COMPLETE RESPONSE", "company_name": "Acacia Pharma"},
        {"application_number": ["NDA 209510"], "letter_date": "01/01/2019",
         "letter_type": "COMPLETE RESPONSE", "company_name": "Acacia Pharma"},
    ]


def test_official_publication_snapshot_remains_quarantined():
    snapshot, audit = build_crl_snapshot(
        metadata(), {URL: make_archive(sample_rows())}, date(2026, 10, 25))
    assert audit["published_letter_records"] == 2
    assert audit["quarantined_records"] == 2
    assert audit["model_eligible"] == 0
    assert audit["full_decision_denominator_verified"] is False
    assert audit["letter_types"]["COMPLETE RESPONSE"] == 2
    assert audit["unique_application_review_cycles_verified"] == 0
    assert all(not row["model_eligible"] for row in snapshot["records"])
    assert all(row["predecision_evidence_as_of"] is None for row in snapshot["records"])
    # A repeated application is preserved as two published letters, never
    # silently treated as two distinct applications or verified review cycles.
    assert len(snapshot["records"]) == 2


def test_download_partition_count_must_reconcile():
    with pytest.raises(ValueError, match="declared partition count"):
        build_crl_snapshot(metadata(n=3), {URL: make_archive(sample_rows())}, date(2026, 10, 25))


def test_invalid_official_host_rejected():
    bad = "https://download.open.fda.gov.attacker.example/transparency/crl/fake.json.zip"
    with pytest.raises(ValueError, match="invalid official CRL download"):
        build_crl_snapshot(metadata(url=bad), {bad: make_archive(sample_rows())}, date(2026, 10, 25))


def test_missing_export_partition_rejected():
    with pytest.raises(ValueError, match="exactly match"):
        build_crl_snapshot(metadata(), {}, date(2026, 10, 25))


def test_future_source_export_rejected():
    data = metadata()
    data["results"]["transparency"]["crl"]["export_date"] = "2099-01-01"
    with pytest.raises(ValueError, match="invalid CRL export"):
        build_crl_snapshot(data, {URL: make_archive(sample_rows())}, date(2026, 10, 25))


def test_invalid_archive_rejected():
    with pytest.raises(ValueError, match="invalid official CRL archive"):
        build_crl_snapshot(metadata(), {URL: b"not a zip"}, date(2026, 10, 25))


def test_missing_application_does_not_get_model_eligible():
    rows = [{"letter_type": "COMPLETE RESPONSE", "letter_date": "10/05/2018"}]
    snapshot, audit = build_crl_snapshot(
        metadata(n=1), {URL: make_archive(rows)}, date(2026, 10, 25))
    assert audit["records_missing_application_number"] == 1
    assert snapshot["records"][0]["model_eligible"] is False
