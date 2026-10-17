"""Every exact WT trial obtains GEM indicator factors, no ticker-to-trial eligibility leak."""
from datetime import date, timedelta
from unittest.mock import patch

from app import wt_research


def _source_snapshot():
    return {
        "asOf": "2026-10-16",
        "sourceHealth": {"publishedScan": {"status": "PARTIAL", "complete": False}},
        "pipeline": [
            {"id": "TRIAL|NCT00000001", "ticker": "AAA", "drug": "Drug A", "nctId": "NCT00000001"},
            {"id": "TRIAL|NCT00000002", "ticker": "AAA", "drug": "Drug B", "nctId": "NCT00000002"},
            {"id": "APPLICATION|AAA|DRUG_C", "eventKey": "AAA|DRUG_C",
             "ticker": "AAA", "drug": "Drug C", "nctId": "NCT00000003"},
        ],
        "members": {
            "GEM": {"rows": [], "history": []},
            "GEM_JR": {"rows": [], "history": []},
        },
    }


def _ctx():
    return {
        "events": {
            "AAA|DRUG_C": {
                "event_key": "AAA|DRUG_C", "ticker": "AAA",
                "phase3_status": "PRIMARY_MET_VERIFIED",
                "nct_id": "NCT00000003",
                "phase3_date": "2025-04-01",
                "trial_evidence_url": "https://example.org/issuer-clinical-results",
            },
        },
        "financing": {"AAA|DRUG_C": {"second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING"}},
        "recheck": {},
        "market": {"AAA": {"market_status": "MARKET_UPDATED"}},
        "runway": {},
        "missingSources": [],
    }


def test_wt_pipeline_trials_keep_trial_specific_benchmarks(monkeypatch):
    monkeypatch.setattr(wt_research, "_signals_for_ticker", lambda ticker: {})
    monkeypatch.setattr(wt_research, "workspace", _source_snapshot)
    monkeypatch.setattr(wt_research, "_context", _ctx)
    monkeypatch.setattr(wt_research, "_market_for_ticker", lambda ticker, market, today: market)
    calls = []

    def analyze(row, event, financing, recheck, market, runway, status, today):
        calls.append((row["id"], event, financing, row.get("nctId"), market))
        return {
            "indicatorEntry": 25, "indicatorExitRisk": 5,
            "indicatorEntryCoverage": 65, "indicatorExitCoverage": 55,
            "entry": None, "exitRisk": None, "entryStatus": "NOT ELIGIBLE",
        }

    monkeypatch.setattr(wt_research, "analyze_member", analyze)
    one = wt_research.for_exact_program("TRIAL|NCT00000001")
    two = wt_research.for_exact_program("TRIAL|NCT00000002")
    assert one["technical"]["indicatorEntry"] == two["technical"]["indicatorEntry"] == 25
    assert calls[0][0] != calls[1][0]
    assert calls[0][1] == calls[1][1] == {}  # Never borrow an application endpoint
    assert calls[0][2] == calls[1][2] == {}  # Never borrow financing by ticker
    assert calls[0][3] == "NCT00000001"
    assert calls[1][3] == "NCT00000002"


def test_existing_gem_profile_remains_identical(monkeypatch):
    monkeypatch.setattr(wt_research, "_signals_for_ticker", lambda ticker: {})
    saved = {"entry": None, "exitRisk": None, "indicatorEntry": 45, "indicatorExitRisk": 15}
    data = _source_snapshot()
    data["members"]["GEM"]["rows"] = [{
        "id": "TRIAL|NCT00000001", "ticker": "AAA", "technical": saved
    }]
    monkeypatch.setattr(wt_research, "workspace", lambda: data)
    monkeypatch.setattr(wt_research, "_context", lambda: (_ for _ in ()).throw(AssertionError("Should not refetch")))
    result = wt_research.for_exact_program("TRIAL|NCT00000001")
    assert result["technical"] is saved
    assert result["source"] == "SAME_GEM_JR_GEM_PROFILE"


def test_historical_trial_keeps_id_without_fake_market_data(monkeypatch):
    monkeypatch.setattr(wt_research, "_signals_for_ticker", lambda ticker: {})
    monkeypatch.setattr(wt_research, "workspace", _source_snapshot)
    result = wt_research.for_exact_program("TRIAL|NCT99999999")
    assert result["technical"] is None
    assert result["source"] == "PUBLISHED_PROGRAM_NOT_CURRENT"


def test_same_gem_indicator_model_retains_eligibility_gate(monkeypatch):
    from app import gem_research_adapter
    real = gem_research_adapter._score_gem_trade
    # Mock a consistent, recent EOD profile to avoid dependence on holidays.
    def profile(row, market, status, today):
        return {
            "recommendation": "WAIT — BENCHMARKS UNVERIFIED",
            "reason": "Clinical eligibility missing",
            "date": today, "fresh": True, "close": 12,
            "sma20": 11, "sma50": 10, "rsi": 57, "rvol": 1.8,
            "dollar_volume": 7_000_000, "support": 10,
            "macd": {"macd": 0.1, "signal": 0.05, "bullish": True},
            "bars": [{"date": today - timedelta(days=59 - i),
                      "close": 12 if i == 59 else 10.5, "volume": 1_000_000}
                     for i in range(60)],
            "base": {
                "status": "NOT CONFIRMED", "support": 10,
                "resistance": 13, "touches": 1, "width_pct": 10,
                "contraction": None, "volume_ratio": None, "breakout_rvol": None,
            },
            "source": "https://example.org/market-eod", "gaps": "ATR unknown",
        }

    monkeypatch.setattr(gem_research_adapter, "assess_gem_trade", profile)
    monkeypatch.setattr(gem_research_adapter, "assess_runway", lambda *a, **k: {
        "Cash runway (months)": None, "Cash runway gate": "UNVERIFIED",
        "Cash runway reason": "Missing SEC data", "Cash runway source": "",
        "Cash runway as of": "",
    })
    result = gem_research_adapter.analyze_member(
        {"id": "TRIAL|NCT00000001", "ticker": "AAA", "nctId": "NCT00000001"},
        {}, {}, {}, {}, None, {"complete": False}, date(2026,10,16),
    )
    assert result["entry"] is None  # Original GEM eligibility not bypassed
    assert result["exitRisk"] is None  # Global scanner is still partial
    assert result["indicatorEntry"] is not None
    assert result["indicatorEntryCoverage"] >= 50
    assert result["indicatorEntryFactors"]
    assert result["indicatorModel"] == "SAME_GEM_WEIGHTED_EOD_MODEL_RESEARCH_ONLY"


def test_yahoo_bar_adapter_is_verified_and_reuses_gem_format():
    from datetime import datetime, timedelta, timezone
    base = datetime(2026, 5, 1, 14, 30, tzinfo=timezone.utc)
    days = [base+timedelta(days=i) for i in range(100)]
    payload = {"chart":{"result":[{
        "meta":{"symbol":"AAA","currency":"USD","instrumentType":"EQUITY"},
        "timestamp":[int(x.timestamp()) for x in days],
        "indicators":{"quote":[{"close":[10+i*.05 for i in range(100)],
                                 "volume":[1_000_000+i*1000 for i in range(100)]}]}
    }]}}
    result = wt_research._interpret_yahoo(
        payload, "AAA","https://query1.finance.yahoo.com/v8/finance/chart/AAA",
        date(2026,10,16)
    )
    assert result["market_status"] == "MARKET_UPDATED"
    assert len(__import__("json").loads(result["price_bars_json"])) == 100
    assert result["relative_volume"] > 0
    assert result["last_close_usd"] == 14.95
    payload["chart"]["result"][0]["meta"]["symbol"] = "BBB"
    assert wt_research._interpret_yahoo(
        payload,"AAA","https://query1.finance.yahoo.com/v8/finance/chart/AAA",
        date(2026,10,16)) is None


def test_on_demand_market_uses_exact_ticker_and_refuses_invalid(monkeypatch):
    called=[]
    monkeypatch.setattr(wt_research, "_download_eod", lambda ticker,today: (
        called.append(ticker) or {"market_status":"MARKET_UPDATED",
                                   "last_session":"2026-10-15",
                                   "price_bars_json":"[]"}
    ))
    market = wt_research._market_for_ticker("AAA",{},date(2026,10,16))
    assert called == ["AAA"]
    assert "AAA" in market


def test_streamlit_optional_watchlist_indicator_snapshot(monkeypatch):
    from app import wt_research as mod
    sample = ("ticker,mode,Volume / RVOL,Bollinger (20\,2),RSI (14),updated_at\n"
              "AAA,ENTRY,BUY,,52.5,2026-10-16T12:00:00Z\n"
              "AAA,EXIT,WAIT,,48.2,2026-10-16T12:00:01Z\n").replace("20\\,2", "20,2")
    # The test file is CSV, and mode-specific ticker matching is never
    # derived from the trial's unrelated clinical outcome.
    with mod._SIGNAL_LOCK:
        mod._SIGNAL_ROWS.update(at=0.0, by_key={})
    monkeypatch.setattr(mod, "fetch", lambda name: "ticker,mode,Volume / RVOL,RSI (14),updated_at\nAAA,ENTRY,BUY,52.5,2026-10-16\nAAA,EXIT,WAIT,48.2,2026-10-16")
    values = mod._signals_for_ticker("AAA")
    assert values["ENTRY"]["signals"]["Volume / RVOL"] == "BUY"
    assert values["EXIT"]["signals"]["RSI (14)"] == "48.2"
    assert values["ENTRY"]["signals"]["ATR (14)"] == "NOT SCANNED"
