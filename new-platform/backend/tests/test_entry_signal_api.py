"""Entry endpoint authenticates and resolves identity on the server."""
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app import main, alpaca_entry_signal


def test_entry_endpoint_requires_authentication(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "entry-api-test-only")
    response = TestClient(main.app).get("/api/entry-signal/PDUFA-000001")
    assert response.status_code == 401


def test_entry_endpoint_uses_registered_program_not_client_ticker(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "entry-api-test-only")
    main.app.dependency_overrides[main.require_storage] = lambda: None
    captured = []
    class Session:
        def __init__(self, *args): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, model, number):
            return SimpleNamespace(ticker="OCGN", source_key="APPLICATION|exact") if number == 1 else None
    def calculate(exact, ticker):
        captured.append((exact, ticker))
        return {"green":False,"status":"WAIT","ticker":ticker}
    monkeypatch.setattr(main, "Session", Session)
    monkeypatch.setattr(alpaca_entry_signal, "entry_for_program", calculate)
    client = TestClient(main.app)
    headers = {"X-PDUFA-Internal-Key":"entry-api-test-only"}
    try:
        response = client.get("/api/entry-signal/PDUFA-000001?ticker=OTHER", headers=headers)
        assert response.status_code == 200
        assert response.json()["ticker"] == "OCGN"
        assert captured == [("APPLICATION|exact", "OCGN")]
        assert client.get("/api/entry-signal/PDUFA-000002", headers=headers).status_code == 404
        assert client.get("/api/entry-signal/invalid", headers=headers).status_code == 422
    finally:
        main.app.dependency_overrides.pop(main.require_storage, None)
