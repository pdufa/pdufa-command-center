"""The ticker-cell Alpaca popup never requires a fabricated program ID."""
from fastapi.testclient import TestClient
from app import main, alpaca_market_chart


def test_ticker_chart_is_authenticated_and_strictly_validated(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "read-only-chart-test")
    client = TestClient(main.app)
    assert client.get("/api/alpaca-ticker/OCGN").status_code == 401
    headers = {"X-PDUFA-Internal-Key": "read-only-chart-test"}
    assert client.get("/api/alpaca-ticker/no!valid", headers=headers).status_code == 422
    assert client.get("/api/alpaca-ticker/OCGN?range=INVALID", headers=headers).status_code == 422


def test_ticker_chart_uses_real_alpaca_provider_without_program_guess(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "read-only-chart-test")
    calls = []
    def fake_alpaca(symbol, range_label):
        calls.append((symbol, range_label))
        return {"provider":"ALPACA", "ticker":symbol, "status":"NOT_CONFIGURED",
                "bars":[], "message":"No provider credentials"}
    monkeypatch.setattr(alpaca_market_chart, "get_alpaca_bars", fake_alpaca)
    client = TestClient(main.app)
    result = client.get("/api/alpaca-ticker/OCGN?range=1Y",
                        headers={"X-PDUFA-Internal-Key":"read-only-chart-test"})
    assert result.status_code == 200
    assert calls == [("OCGN", "1Y")]
    assert result.json()["programId"] is None
    assert result.json()["bars"] == []
