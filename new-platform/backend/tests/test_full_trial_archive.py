import gzip
import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import full_trial_archive as archive, main


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(archive, "_scope", lambda: ["NCT00000001", "NCT00000002"])
    monkeypatch.setattr(archive.time, "sleep", lambda _: None)
    yield engine
    engine.dispose()


def study(nct="NCT00000001"):
    return {
        "protocolSection": {"identificationModule": {"nctId": nct, "briefTitle": "A trial"},
                            "designModule": {"phases": ["PHASE1"]},
                            "outcomesModule": {"primaryOutcomes": [{"measure": "A priori p < 0.05"}]}},
        "hasResults": True,
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{
            "type": "PRIMARY", "title": "Primary endpoint", "timeFrame": "12 weeks",
            "groups": [{"id": "OG000", "title": "Drug"}, {"id": "OG001", "title": "Placebo"}],
            "analyses": [{"groupIds": ["OG000", "OG001"], "pValue": "<0.0001",
                          "paramValue": "1.2", "ciLowerLimit": "0.4", "ciUpperLimit": "2.0",
                          "unknownFutureStatistic": {"keep": [0, False, None]}}],
        }, {"type": "SECONDARY", "title": "Secondary endpoint", "analyses": [{"pValue": 0}]}]}},
        "documentSection": {"protocolSection": [{"filename": "protocol.pdf"}]},
        "unknownFutureSection": {"complete": True, "empty": [], "zero": 0},
    }


def test_all_fields_and_p_values_remain_lossless(isolated):
    archive.start_download(launch=False)
    originals = {nct: study(nct) for nct in archive._scope()}
    archive.run_download(lambda ids: {nct: originals[nct] for nct in ids})
    status = archive.archive_status()
    assert status["complete"] and status["downloaded"] == 2
    assert status["reportedPValues"] == 4
    with Session(isolated) as session:
        record = session.get(main.FullTrialRecord, "NCT00000001")
        assert json.loads(gzip.decompress(record.payload_gzip)) == originals["NCT00000001"]
        assert record.statistics[0]["comparison_groups"][0]["title"] == "Drug"
        assert record.statistics[0]["p_value"] == "<0.0001"
        assert record.statistics[1]["p_value"] == 0

def test_protocol_threshold_is_not_a_reported_result():
    value = study()
    value.pop("resultsSection")
    value["hasResults"] = False
    assert archive.statistics(value) == []
    assert archive.summarize(value, [])["p_value_status"] == "NO_POSTED_RESULTS"


def test_missing_studies_stay_partial_and_retry_resumes(isolated):
    archive.start_download(launch=False)
    archive.run_download(lambda ids: {"NCT00000001": study()})
    assert archive.archive_status()["status"] == "PARTIAL"
    seen = []
    def retry(ids):
        seen.extend(ids)
        return {nct: study(nct) for nct in ids}
    archive.start_download(launch=False)
    archive.run_download(retry)
    assert seen == ["NCT00000002"]
    assert archive.archive_status()["complete"]
    assert archive.archive_status()["reportedPValues"] == 4


def test_retired_zip_cache_cleanup_only_deletes_generated_export_files(monkeypatch, tmp_path):
    monkeypatch.setattr(archive.tempfile, "gettempdir", lambda: str(tmp_path))
    completed = tmp_path / "pdufa-full-trial-export.zip"
    partial = tmp_path / "pdufa-full-trial-export.building"
    original = tmp_path / "trial-data.json"
    completed.write_bytes(b"archived-zip")
    partial.write_bytes(b"partial")
    original.write_bytes(b"preserve")
    assert archive.cleanup_retired_zip_exports() == {"removed": 2, "bytes": 19}
    assert not completed.exists() and not partial.exists()
    assert original.read_bytes() == b"preserve"
    assert archive.cleanup_retired_zip_exports() == {"removed": 0, "bytes": 0}


def _route_paths(routes):
    """Walk ordinary and lazy included routers without dropping nested routes."""
    paths = set()
    for route in routes:
        nested = getattr(route, "original_router", None)
        if nested is not None:
            paths.update(_route_paths(nested.routes))
        elif hasattr(route, "path"):
            paths.add(route.path)
    return paths


def test_bulk_zip_download_endpoints_are_removed():
    routes = _route_paths(main.app.routes)
    assert "/api/pipeline-full-records/export-link" not in routes
    assert "/downloads/pipeline-all-fields/{ticket}" not in routes



def test_paged_summaries_and_record_capabilities_preserve_every_field(isolated, monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-record-key")
    archive.start_download(launch=False)
    originals = {nct: study(nct) for nct in archive._scope()}
    archive.run_download(lambda ids: {nct: originals[nct] for nct in ids})
    listing = archive.record_summaries("NCT00000001,NCT99999999")
    assert listing["missing"] == ["NCT99999999"]
    summary = listing["records"]["NCT00000001"]
    assert summary["p_value_count"] == 2
    assert summary["phases"] == ["PHASE1"]
    assert "brief_summary" not in summary
    path = archive.make_record_ticket("NCT00000001")
    ticket = path.rsplit("/", 1)[-1]
    response = archive.record_response("NCT00000001", ticket)
    assert json.loads(response.body) == originals["NCT00000001"]
    assert response.headers["access-control-allow-origin"] == "*"
    # A trial ticket cannot read another NCT ID.
    with pytest.raises(HTTPException):
        archive.record_response("NCT00000002", ticket)
    with pytest.raises(HTTPException):
        archive.record_summaries("not-a-trial")
    with pytest.raises(HTTPException):
        archive.record_summaries(",".join(f"NCT{i:08d}" for i in range(51)))


def test_record_view_http_flow_requires_app_auth_and_valid_exact_trial_ticket(isolated, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-only-http-key")
    monkeypatch.setattr(main, "REQUIRE_POSTGRES", False)
    archive.start_download(launch=False)
    archive.run_download(lambda ids: {nct: study(nct) for nct in ids})
    client = TestClient(main.app)
    path = "/api/pipeline-full-records/rows?ids=NCT00000001"
    assert client.get(path).status_code == 401
    headers = {"x-pdufa-internal-key": "test-only-http-key"}
    listing = client.get(path, headers=headers)
    assert listing.status_code == 200
    assert listing.json()["records"]["NCT00000001"]["p_value_count"] == 2
    sort_path = "/api/pipeline-full-records/sort-index"
    assert client.get(sort_path).status_code == 401
    sort_index = client.get(sort_path, headers=headers)
    assert sort_index.status_code == 200
    assert sort_index.json()["count"] == 2
    assert sort_index.json()["records"]["NCT00000001"] == {
        "status": "", "primary_completion_date": None, "p_value_count": 2,
    }
    link = client.get("/api/pipeline-full-records/NCT00000001/view-link", headers=headers)
    assert link.status_code == 200
    record = client.get(link.json()["path"], headers={"Origin": "https://pdufa-new-dashboard.vercel.app"})
    assert record.status_code == 200
    assert record.json() == study()
    assert record.headers["x-record-sha256"]
    assert record.headers["access-control-allow-origin"] == "*"

