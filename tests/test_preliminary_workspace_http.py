import pytest
from research.preliminary_workspace_http import make_workspace_get


@pytest.mark.parametrize("origin", [
    "http://example.com", "https://user:pass@example.com",
    "https://example.com/path", "https://example.com?x=1",
])
def test_rejects_unsafe_origin(origin):
    with pytest.raises(ValueError):
        make_workspace_get(origin, api_key="test")


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("PDUFA_INTERNAL_API_KEY", raising=False)
    with pytest.raises(ValueError, match="required"):
        make_workspace_get("https://example.com")


def test_http_get_uses_only_protected_read_endpoint(monkeypatch):
    observed = {}
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit):
            return b'{"version":"v1","rows":[],"total":0,"offset":0,"limit":100,"nextOffset":null}'
    def fake_urlopen(request, timeout):
        observed["method"] = request.get_method()
        observed["url"] = request.full_url
        observed["key"] = request.get_header("X-pdufa-internal-key")
        return Response()
    monkeypatch.setattr("research.preliminary_workspace_http.urlopen", fake_urlopen)
    get = make_workspace_get("https://example.com", api_key="secret-test")
    result = get(offset=0, limit=100, version="")
    assert result["total"] == 0
    assert observed["method"] == "GET"
    assert observed["url"].startswith("https://example.com/api/workspace/page?")
    assert observed["key"] == "secret-test"


def test_aggregate_diagnostics_never_expose_program_records(monkeypatch):
    from research import preliminary_workspace_http as http
    monkeypatch.setattr(http, "screen_backend_workspace", lambda *args, **kwargs: {
        "workspace_version": "v1", "workspace_as_of": "2026-10-29",
        "backend_rows_received": 1, "market_cap_evidence_present": 1,
        "fda_target_evidence_present": 0, "candidate_for_evidence_review": 0,
        "blocked": 1, "prediction_status": "ABSTAIN",
        "data_authenticity_verified": False,
        "records": [{"program_id": "PDUFA-000001", "secret": "must-not-appear"}]})
    result = http.safe_workspace_diagnostics("https://example.com")
    assert "records" not in result
    assert "must-not-appear" not in repr(result)
    assert result["prediction_status"] == "ABSTAIN"
