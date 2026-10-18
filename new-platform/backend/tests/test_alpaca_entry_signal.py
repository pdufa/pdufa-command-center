"""Entry rules: source integrity, no lookahead, exact-program gates and timing."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import pytest
from app import alpaca_entry_signal as entry

NOW = datetime(2026, 10, 19, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def fixture():
    calendar = entry.session_context(NOW)
    bars = [dict(date=d, open=4.85, high=5., low=4.7, close=4.85,
                 volume=200000., vwap=4.85) for d in calendar["recentSessions"]]
    bars[-1].update(high=5.10, close=5.06, volume=320000., vwap=5.)
    anchor = date.fromisoformat(bars[5]["date"])
    return bars, calendar, anchor


def test_entry_numbers_and_thresholds(fixture):
    bars, calendar, anchor = fixture
    result = entry.calculate(bars, anchor=anchor, calendar=calendar)
    assert result["setupConfirmed"] is True
    assert result["entryTrigger"] == 5.03
    assert result["maximumEntry"] == 5.18
    assert result["initialStop"] == 4.62
    assert result["rvol20"] == 1.6
    assert result["atr14"] == pytest.approx(.3)


def test_signal_day_does_not_change_base_atr_or_average(fixture):
    bars, calendar, anchor = fixture
    original = entry.calculate(bars, anchor=anchor, calendar=calendar)
    bars[-1].update(high=9., volume=400000.)
    changed = entry.calculate(bars, anchor=anchor, calendar=calendar)
    for key in ("entryTrigger", "maximumEntry", "initialStop", "atr14", "baseHigh", "baseLow"):
        assert changed[key] == original[key]
    assert changed["rvol20"] == 2.


def test_volume_and_lower_low_each_prevent_confirmation(fixture):
    bars, calendar, anchor = fixture
    bars[-1]["volume"] = 299999
    assert not entry.calculate(bars, anchor=anchor, calendar=calendar)["setupConfirmed"]
    bars[-1]["volume"] = 320000
    bars[-2]["low"] = 4.69
    result = entry.calculate(bars, anchor=anchor, calendar=calendar)
    assert not next(c for c in result["checks"] if c["label"] == "Stabilizing lows")["pass"]


def test_missing_history_stale_day_and_anchor_coverage(fixture):
    bars, calendar, anchor = fixture
    with pytest.raises(ValueError):
        entry.calculate(bars[1:], anchor=anchor, calendar=calendar)
    bad = deepcopy(bars)
    bad[-1]["date"] = "2026-10-15"
    with pytest.raises(ValueError):
        entry.calculate(bad, anchor=anchor, calendar=calendar)
    with pytest.raises(ValueError):
        entry.calculate(bars, anchor=date(2020, 1, 1), calendar=calendar)


def test_exchange_calendar_handles_holidays_and_early_close():
    holiday = entry.session_context(datetime(2026, 9, 7, 20, tzinfo=timezone.utc))
    assert holiday["expectedSession"] == "2026-09-04"
    assert holiday["entrySession"] == "2026-09-08"
    early = entry.session_context(datetime(2026, 11, 27, 18, 25, tzinfo=timezone.utc))
    assert early["expectedSession"] == "2026-11-27"
    assert early["entrySession"] == "2026-11-30"


def test_history_explicitly_requests_delayed_split_adjusted_sip(monkeypatch, fixture):
    bars, calendar, anchor = fixture
    calls = []
    def request(path, params):
        calls.append(params)
        return {"bars": [dict(t=b["date"]+"T04:00:00Z", o=b["open"], h=b["high"],
                              l=b["low"], c=b["close"], v=b["volume"], vw=b["vwap"]) for b in bars]}
    monkeypatch.setattr(entry, "_request", request)
    entry._CACHE.clear()
    result = entry.history("TEST", anchor, calendar["expectedSession"], NOW)
    assert len(result) == 61
    assert calls[0]["feed"] == "sip" and calls[0]["adjustment"] == "split"
    assert datetime.fromisoformat(calls[0]["end"]) <= NOW-timedelta(minutes=15)


def test_stale_or_crossed_quote_is_rejected(monkeypatch):
    monkeypatch.setattr(entry, "_request", lambda *args: {"quote": {"t": (NOW-timedelta(seconds=61)).isoformat(),"bp":5.04,"ap":5.05}})
    with pytest.raises(ValueError): entry.live_quote("TEST", NOW)
    monkeypatch.setattr(entry, "_request", lambda *args: {"quote": {"t":NOW.isoformat(),"bp":5.08,"ap":5.05}})
    with pytest.raises(ValueError): entry.live_quote("TEST", NOW)


@pytest.fixture
def program(monkeypatch, fixture):
    from app import source_workspace, wt_research
    bars, calendar, anchor = fixture
    row = {"id":"APPLICATION|test", "ticker":"TEST", "nctId":"NCT00000001",
           "eventKey":"test", "pdufaDate":"2026-12-15"}
    event = {"event_key":"test", "ticker":"TEST", "phase3_date":"2026-01-01",
             "phase3_status":"VERIFIED_SUCCESS", "trial_evidence_url":"https://issuer.test/readout",
             "nct_id":"NCT00000001", "pdufa_date":"2026-12-15",
             "pdufa_confirmation":"VERIFIED", "pdufa_evidence_url":"https://issuer.test/pdufa",
             "new_dilution_flag":"NO"}
    context = {"events":{"test":event}, "financing":{"test":{
        "first_financing_date":"2026-02-01", "second_financing_date":anchor.isoformat(),
        "second_financing_audit_status":"VERIFIED_SECOND_POST_PHASE3_FINANCING"}},
        "recheck":{"test":{"first_sec_status":"VERIFIED", "second_sec_status":"VERIFIED",
        "first_sec_url":"https://sec.gov/first", "second_sec_url":"https://sec.gov/second",
        "gem_entry_authorized":"YES"}}, "missingSources":[]}
    snapshot = {"members":{"GEM":{"rows":[row]}}, "sourceHealth":{
        "state":"CURRENT", "publishedScan":{"complete":True,"finishedAt":(NOW-timedelta(hours=1)).isoformat()}}}
    monkeypatch.setattr(source_workspace, "workspace", lambda: snapshot)
    monkeypatch.setattr(wt_research, "_context", lambda: context)
    # Include a real pre-readout anchor observation in the mocked history;
    # without it, the Phase 3 AVWAP must remain unavailable rather than guess.
    historic = [dict(date="2025-12-31", open=4.85, high=5., low=4.7,
                     close=4.85, volume=200000., vwap=4.85)] + bars
    monkeypatch.setattr(entry, "history", lambda *args: historic)
    monkeypatch.setattr(entry, "live_quote", lambda *args: {"bid":5.04,"ask":5.05,"asOf":NOW.isoformat(),"feed":"IEX"})
    return row, event, context, snapshot


def test_green_only_for_all_checks_and_current_entry_price(program):
    result = entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)
    assert result["green"] is True and result["status"] == "BUY"
    assert result["orderExecutionEnabled"] is False


def test_optional_financing_does_not_block_green_or_borrow_unverified_anchor(program):
    _, _, context, _ = program
    context["recheck"]["test"]["gem_entry_authorized"] = "NO"
    result = entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)
    assert result["green"] is True
    assert result["secondFinancingVerified"] is False
    assert result["anchorType"] == "PHASE3_READOUT"
    assert not entry.entry_for_program("TRIAL|NCT00000001", "TEST", now=NOW)["green"]


def test_unknown_or_unresolved_dilution_still_blocks_buy(program):
    _, event, context, _ = program
    for status in ("", "UNKNOWN", "UNRESOLVED", "YES"):
        event["new_dilution_flag"] = status
        result = entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)
        assert result["green"] is False
        assert result["status"] == "WAIT"
    event["new_dilution_flag"] = "NO"


def test_no_green_for_extended_price_or_unavailable_quote(program, monkeypatch):
    monkeypatch.setattr(entry, "live_quote", lambda *a: {"bid":5.3,"ask":5.31,"asOf":NOW.isoformat(),"feed":"IEX"})
    result = entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)
    assert result["status"] == "WAIT" and not result["green"]
    def unavailable(*a): raise ValueError("stale")
    monkeypatch.setattr(entry, "live_quote", unavailable)
    assert entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)["status"] == "UNAVAILABLE"


def test_no_green_for_weekend_exit_window_or_stale_sources(program):
    row, event, _, snapshot = program
    saturday = NOW-timedelta(days=2)
    snapshot["sourceHealth"]["publishedScan"]["finishedAt"] = (saturday-timedelta(hours=1)).isoformat()
    result = entry.entry_for_program("APPLICATION|test", "TEST", now=saturday)
    assert result["status"] == "READY_NEXT_SESSION" and not result["green"]
    row["pdufaDate"] = event["pdufa_date"] = "2026-10-30"
    snapshot["sourceHealth"]["publishedScan"]["finishedAt"] = NOW.isoformat()
    result = entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)
    assert result["status"] == "WAIT" and not result["green"]
    row["pdufaDate"] = event["pdufa_date"] = "2026-12-15"
    snapshot["sourceHealth"]["publishedScan"]["finishedAt"] = (NOW-timedelta(days=4)).isoformat()
    assert entry.entry_for_program("APPLICATION|test", "TEST", now=NOW)["status"] == "UNAVAILABLE"
