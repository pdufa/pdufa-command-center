"""Strict Alpaca-only chart provider and incomplete-bar safety tests."""
from datetime import datetime, timezone
from unittest.mock import patch

from app import alpaca_market_chart as market


def make_bars(n=64):
    from datetime import timedelta
    first = datetime(2026, 1, 5, 5, tzinfo=timezone.utc)
    raw = []
    for i in range(n):
        day = first + timedelta(days=i)
        raw.append({
            "t": day.isoformat().replace("+00:00", "Z"),
            "o": 8.0 + i * .03, "h": 8.4 + i * .03,
            "l": 7.7 + i * .03, "c": 8.2 + i * .03,
            "v": 25000 + i * 150,
        })
    return {"bars": raw}


def test_alpaca_chart_no_keys_no_fallback(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    monkeypatch.delenv("APCA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_SECRET_KEY", raising=False)
    monkeypatch.delenv("APCA_API_SECRET_KEY", raising=False)
    result = market.get_alpaca_bars("OCGN", "6M")
    assert result["status"] == "NOT_CONFIGURED"
    assert result["bars"] == []
    assert result["provider"] == "ALPACA"
    assert result["orderExecutionEnabled"] is False


def test_market_data_rejects_corrupt_ohlc_and_duplicate_day():
    now = datetime(2026,10,16,23,tzinfo=timezone.utc)
    response = make_bars()
    response["bars"][0]["h"] = 1
    response["bars"].append(response["bars"][1])
    valid = market._parse_bars(response, "OCGN", now)
    assert len(valid) == 63
    assert all(x["high"] >= x["close"] >= x["low"] for x in valid)


def test_alpaca_chart_refuses_invalid_symbol_even_with_keys(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "paper-test")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "paper-secret")
    result = market.get_alpaca_bars("../../secrets", "6M")
    assert result["status"] == "INVALID_SYMBOL"
    assert result["bars"] == []


def test_alpaca_chart_feed_default_iex(monkeypatch):
    monkeypatch.delenv("ALPACA_DATA_FEED", raising=False)
    assert market._feed() == "iex"
    monkeypatch.setenv("ALPACA_DATA_FEED", "sip")
    assert market._feed() == "sip"
    monkeypatch.setenv("ALPACA_DATA_FEED", "ftp://evil")
    assert market._feed() == "iex"


def test_alpaca_current_daily_bar_is_withheld_before_close():
    response = {"bars":[{"t":"2026-10-16T04:00:00Z","o":2,"h":3,"l":1,"c":2,"v":1000}]}
    before = datetime(2026,10,16,17,0,tzinfo=timezone.utc)
    assert market._parse_bars(response, "OCGN", before) == []
    after = datetime(2026,10,16,21,0,tzinfo=timezone.utc)
    assert len(market._parse_bars(response, "OCGN", after)) == 1


def test_alpaca_empty_history_is_not_global_provider_outage(monkeypatch):
    """Acquired/delisted symbols commonly return bars:null or an empty list."""
    import io
    import json
    monkeypatch.setenv("ALPACA_API_KEY", "mock-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "mock-secret")
    market._CACHE.clear()
    for ticker, response_bars in (("VIE", None), ("AIMT", []), ("EPZM", None)):
        data = json.dumps({"bars": response_bars, "next_page_token": None}).encode("utf-8")
        monkeypatch.setattr(market, "urlopen",
                            lambda request, timeout=9, raw=data: io.BytesIO(raw))
        result = market.get_alpaca_bars(ticker, "6M")
        assert result["status"] == "NO_MARKET_HISTORY"
        assert result["provider"] == "ALPACA"
        assert result["bars"] == []
        assert "No current price or trading signal" in result["message"]
        assert result["orderExecutionEnabled"] is False
    market._CACHE.clear()


def test_alpaca_malformed_response_stays_untrusted(monkeypatch):
    import io
    monkeypatch.setenv("ALPACA_API_KEY", "mock-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "mock-secret")
    market._CACHE.clear()
    monkeypatch.setattr(market, "urlopen", lambda *args, **kwargs: io.BytesIO(b'{"oops":true}'))
    result = market.get_alpaca_bars("OCGN", "6M")
    assert result["status"] == "INVALID_SOURCE_RESPONSE"
    assert result["bars"] == []
    market._CACHE.clear()


def test_alpaca_chart_cache_is_bounded(monkeypatch):
    import io
    monkeypatch.setenv("ALPACA_API_KEY", "mock-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "mock-secret")
    market._CACHE.clear()
    monkeypatch.setattr(market, "urlopen", lambda *args, **kwargs: io.BytesIO(b'{"bars":null}'))
    for n in range(market.MAX_CACHE_ENTRIES + 6):
        result = market.get_alpaca_bars(f"ZZTEST{n}", "6M")
        assert result["status"] == "NO_MARKET_HISTORY"
    assert len(market._CACHE) <= market.MAX_CACHE_ENTRIES
    market._CACHE.clear()
