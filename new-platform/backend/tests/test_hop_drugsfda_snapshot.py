import io
import json
import zipfile
from datetime import date

import pytest

from app.hop_drugsfda_snapshot import stage_drugsfda_manifest

URL = "https://download.open.fda.gov/drug/drugsfda/drug-drugsfda-0001-of-0001.json.zip"


def archive(rows):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("drug-drugsfda-0001.json", json.dumps({"results": rows}))
    return buffer.getvalue()


def manifest(n=2, url=URL):
    return {"results": {"drug": {"drugsfda": {
        "export_date": "2026-10-23",
        "total_records": n,
        "partitions": [{"file": url, "records": n}],
    }}}}


def records():
    return [
        {"application_number": "NDA123456", "sponsor_name": "Example sponsor",
         "submissions": [{"submission_type": "ORIG", "submission_number": "1",
                          "submission_status": "AP", "submission_status_date": "20200102"}]},
        {"application_number": "ANDA000001", "sponsor_name": "Example generic",
         "submissions": [{"submission_type": "ORIG", "submission_number": "1",
                          "submission_status": "AP", "submission_status_date": "20200601"}]},
    ]


def test_registry_is_never_approval_probability_denominator():
    snap, audit = stage_drugsfda_manifest(
        manifest(), {URL: archive(records())}, date(2026,10,25))
    assert audit["source_application_records"] == 2
    assert audit["quarantined_application_records"] == 2
    assert audit["application_number_prefixes"] == {"ANDA": 1, "NDA": 1}
    assert audit["model_eligible_records"] == 0
    assert audit["complete_original_nda_bla_denominator_verified"] is False
    assert audit["published_submission_status_counts"]["AP"] == 2
    assert len(snap["records"]) == 2
    assert all(row["model_eligible"] is False for row in snap["records"])


def test_duplicate_source_applications_not_silently_removed():
    rows = [records()[0], records()[0]]
    snap, audit = stage_drugsfda_manifest(
        manifest(), {URL: archive(rows)}, date(2026,10,25))
    assert audit["duplicate_application_identifiers"] == 1
    assert len(snap["records"]) == 2


def test_mismatch_count_fails():
    with pytest.raises(ValueError, match="partition count"):
        stage_drugsfda_manifest(manifest(n=3), {URL: archive(records())}, date(2026,10,25))


def test_official_download_host_required():
    bad = "https://download.open.fda.gov.attacker.test/drug/drugsfda/x.json.zip"
    with pytest.raises(ValueError, match="unapproved Drugs@FDA archive"):
        stage_drugsfda_manifest(manifest(url=bad), {bad: archive(records())}, date(2026,10,25))


def test_missing_partitions_fails():
    with pytest.raises(ValueError, match="must match manifest"):
        stage_drugsfda_manifest(manifest(), {}, date(2026,10,25))


def test_future_export_fails():
    m = manifest()
    m["results"]["drug"]["drugsfda"]["export_date"] = "2099-01-01"
    with pytest.raises(ValueError, match="invalid Drugs@FDA source manifest"):
        stage_drugsfda_manifest(m, {URL: archive(records())}, date(2026,10,25))


def test_bad_zip_fails():
    with pytest.raises(ValueError, match="invalid Drugs@FDA source archive"):
        stage_drugsfda_manifest(manifest(), {URL: b"bad zip"}, date(2026,10,25))
