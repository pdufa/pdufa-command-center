"""Exact-NCT source cache recovery regressions."""
from datetime import datetime, timezone
import importlib.util
import io
import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "pool_registry_resume_source", ROOT/"scripts/collect_deep_medical_intelligence.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
NCT = "NCT00000001"


def packet():
    return {"protocolSection": {"identificationModule": {"nctId": NCT}}}


def test_missing_cached_packet_with_today_receipt_refetches(tmp_path):
    client = m.RegistryClient(report=tmp_path, retries=1)
    client.state["sources"][NCT] = {"nctId": NCT, "versions": [],
        "lastSuccessfulRemoteRetrievalAt": datetime.now(timezone.utc).isoformat()}
    called = []
    def opener(*a, **k):
        called.append(a)
        return io.BytesIO(json.dumps(packet()).encode())
    with patch.object(m, "urlopen", opener):
        nct, value, error, origin = client.fetch(NCT, resume=True)
    assert nct == NCT and value == packet()
    assert error is None and origin == "OFFICIAL_CT_GOV_API_V2"
    assert len(called) == 1


def test_valid_today_packet_is_reused_without_network(tmp_path):
    client = m.RegistryClient(report=tmp_path, retries=1)
    client.accept(NCT, packet(), "OFFICIAL_CT_GOV_API_V2",
                  datetime.now(timezone.utc).isoformat())
    with patch.object(m, "urlopen", side_effect=AssertionError("No network call")):
        nct, value, error, origin = client.fetch(NCT, resume=True)
    assert value == packet() and error is None
    assert origin == "RESUMED_CURRENT_DAY_REMOTE_CAPTURE"


def test_successful_retry_supersedes_prior_failure_but_preserves_history():
    events = [{"nctId": NCT, "error": "HTTPError"},
              {"nctId": "NCT00000002", "error": None},
              {"nctId": NCT, "error": None}]
    selected = {NCT, "NCT00000002"}
    assert m.latest_source_job_status(selected, events) == "COMPLETED"
    assert events[0]["error"] == "HTTPError"
    assert m.latest_source_job_status(selected, events[:-1]) == "COMPLETED_WITH_SOURCE_ERRORS"
    assert m.latest_source_job_status(selected | {"NCT00000003"}, events) == "COMPLETED_WITH_SOURCE_ERRORS"
