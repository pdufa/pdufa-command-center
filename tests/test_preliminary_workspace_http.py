import pytest
from research.preliminary_workspace_http import make_workspace_get


@pytest.mark.parametrize("origin", [
    "http://example.com", "https://user:pass@example.com",
    "https://example.com/path", "https://example.com?x=1",
])
def test_rejects_unsafe_origin(origin):
    with pytest.raises(ValueError):
        make_workspace_get(origin, api_key="test", allow_identity_allocation=True)


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.delenv("PDUFA_INTERNAL_API_KEY", raising=False)
    with pytest.raises(ValueError, match="required"):
        make_workspace_get("https://example.com", allow_identity_allocation=True)


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
    get = make_workspace_get("https://example.com", api_key="secret-test", allow_identity_allocation=True)
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


@pytest.mark.parametrize('raw', [b'{"total":1,"total":2}', b'{"total":NaN}', b'[]'])
def test_ambiguous_or_nonfinite_json_is_rejected_without_response_disclosure(monkeypatch, raw):
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return raw
    monkeypatch.setattr('research.preliminary_workspace_http.urlopen', lambda *a, **k: Response())
    get = make_workspace_get('https://example.com', api_key='SYNTHETIC_SECRET', allow_identity_allocation=True)
    with pytest.raises(ValueError, match='invalid workspace JSON') as caught:
        get(offset=0, limit=100, version='')
    assert 'SYNTHETIC_SECRET' not in str(caught.value)
    assert raw.decode() not in str(caught.value)


def test_internal_key_is_never_forwarded_through_redirect(monkeypatch):
    from urllib.error import HTTPError
    from research import preliminary_workspace_http as http
    calls = []
    class Opener:
        def open(self, request, timeout):
            calls.append(request.full_url)
            raise HTTPError(request.full_url, 302, 'SYNTHETIC_SECRET',
                            {'Location': 'https://unrelated.example/collect'}, None)
    def builder(handler):
        assert handler.redirect_request(None, None, 302, None, {}, 'https://unrelated.example') is None
        return Opener()
    monkeypatch.setattr(http, 'build_opener', builder)
    get = http.make_workspace_get('https://example.com', api_key='SYNTHETIC_SECRET', allow_identity_allocation=True)
    with pytest.raises(ValueError, match='unavailable or access denied') as caught:
        get(offset=0, limit=100, version='')
    assert len(calls) == 1
    assert calls[0].startswith('https://example.com/')
    assert 'SYNTHETIC_SECRET' not in str(caught.value)


def test_authenticated_summary_and_pages_are_reconciled_end_to_end(monkeypatch):
    from datetime import datetime, timezone
    import json
    from urllib.parse import parse_qs, urlparse
    from research import preliminary_workspace_http as http
    stamp = datetime.now(timezone.utc).isoformat()
    paths = []
    class Response:
        status = 200
        def __init__(self, content): self.content = content
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, limit): return json.dumps(self.content).encode()
    def transport(request, timeout):
        assert request.get_header('X-pdufa-internal-key') == 'SYNTHETIC_SECRET'
        url = urlparse(request.full_url)
        paths.append(url.path)
        if url.path.endswith('/summary'):
            return Response({'pipeline': 101, 'asOf': stamp, 'sourceState': 'PARTIAL'})
        query = parse_qs(url.query)
        offset = int(query['offset'][0])
        if offset:
            assert query['version'] == ['snapshot-v1']
        return Response({'version': 'snapshot-v1', 'asOf': stamp, 'total': 101,
            'offset': offset, 'limit': 100,
            'rows': [{'programId': f'PDUFA-{i:06d}'} for i in range(offset, min(offset + 100, 101))],
            'nextOffset': 100 if offset == 0 else None})
    monkeypatch.setattr(http, 'urlopen', transport)
    report = http.safe_workspace_diagnostics('https://example.com', api_key='SYNTHETIC_SECRET',
                                             allow_identity_allocation=True)
    assert paths == ['/api/workspace/summary', '/api/workspace/page', '/api/workspace/page', '/api/workspace/summary']
    assert report['backend_rows_received'] == report['blocked'] == 101
    assert report['summary_reconciled'] and report['retrieval_complete']
    assert 'records' not in report
    assert 'SYNTHETIC_SECRET' not in repr(report)


def test_operator_runner_fails_before_network_when_key_missing(monkeypatch, tmp_path):
    from research import preliminary_workspace_http as http
    monkeypatch.delenv('PDUFA_INTERNAL_API_KEY', raising=False)
    monkeypatch.setattr(http, 'urlopen', lambda *a, **k: pytest.fail('unexpected network request'))
    output = tmp_path / 'diagnostics.json'
    with pytest.raises(SystemExit) as caught:
        http.main(['--backend-origin', 'https://example.com', '--output', str(output),
                   '--allow-staging-identity-allocation'])
    assert caught.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize('origin', ['https://example.com:8443', 'https://example.com:broken',
                                    'https://example.com/\n'])
def test_origin_cannot_hide_unsafe_ports_or_control_characters(origin):
    with pytest.raises(ValueError):
        make_workspace_get(origin, api_key='SYNTHETIC_SECRET', allow_identity_allocation=True)


@pytest.mark.parametrize('approval', [False, None, 'true', 1])
def test_bulk_retrieval_requires_explicit_database_side_effect_authorization(monkeypatch, approval):
    from research import preliminary_workspace_http as http
    monkeypatch.setattr(http, 'make_workspace_client', lambda *a, **k: pytest.fail('client created before authorization'))
    with pytest.raises(ValueError, match='explicit authorization'):
        http.screen_backend_workspace('https://example.com', api_key='SYNTHETIC_SECRET',
                                       allow_identity_allocation=approval)


def test_operator_runner_never_contacts_backend_without_allocation_authorization(monkeypatch, tmp_path):
    from research import preliminary_workspace_http as http
    monkeypatch.setenv('PDUFA_INTERNAL_API_KEY', 'SYNTHETIC_SECRET')
    monkeypatch.setattr(http, 'make_workspace_client', lambda *a, **k: pytest.fail('unexpected backend request'))
    output = tmp_path / 'report.json'
    with pytest.raises(SystemExit) as caught:
        http.main(['--backend-origin', 'https://example.com', '--output', str(output)])
    assert caught.value.code == 2
    assert not output.exists()


@pytest.mark.parametrize('factory_name', ['make_workspace_get', 'make_workspace_client',
                                        'screen_backend_workspace', 'safe_workspace_diagnostics'])
@pytest.mark.parametrize('approval', [False, None, 'true', 1])
def test_all_http_entrypoints_fail_closed_before_network(monkeypatch, factory_name, approval):
    from research import preliminary_workspace_http as http
    monkeypatch.setattr(http, 'urlopen', lambda *a, **k: pytest.fail('unauthorized network request'))
    with pytest.raises(ValueError, match='explicit authorization'):
        getattr(http, factory_name)('https://example.com', api_key='SYNTHETIC_SECRET',
                                    allow_identity_allocation=approval)
