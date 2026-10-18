"""Alpaca issuer price research is separate from clinical-trial eligibility."""
from datetime import date,datetime,timedelta,timezone

from fastapi.testclient import TestClient
from app import main,alpaca_trial_selection


def sample():
    rows=[]
    d=date(2026,6,1)
    while len(rows)<85:
        if d.weekday()<5:
            n=len(rows);px=20+n*.03
            rows.append({"date":d.isoformat(),"open":px,"high":px+.20,
                         "low":px-.20,"close":px,"volume":100000})
        d+=timedelta(days=1)
    return rows


def test_selection_metrics_are_research_only_and_dated():
    rows=sample()
    calendar={"recentSessions":[r["date"] for r in rows[-61:]]}
    result=alpaca_trial_selection.summarize(rows,calendar,"sip")
    assert result["status"]=="OK"
    assert result["provider"]=="ALPACA"
    assert result["feedCoverage"]=="SIP_CONSOLIDATED"
    assert result["noPositionOrTradingAccess"] is True
    assert result["programEligibilityVerified"] is False
    assert result["sma20"]>0
    assert result["sma50"]>0
    assert result["rvol20"]==1
    assert result["change20Pct"]>0


def test_missing_sessions_fail_closed_and_iex_marked():
    rows=sample()
    complete={"recentSessions":[r["date"] for r in rows[-61:]]}
    iex=alpaca_trial_selection.summarize(rows,complete,"iex")
    assert iex["feedCoverage"]=="IEX_SINGLE_EXCHANGE"
    assert iex["volumeConfirmed"] is None
    rows.pop(-8)
    try:
        alpaca_trial_selection.summarize(rows,complete,"sip")
    except ValueError:
        pass
    else:
        assert False,"Session gaps must not produce a complete technical ranking"


def test_backend_trial_selection_requires_current_stage_membership(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY","test-trial-only")
    monkeypatch.setattr("app.source_workspace.workspace",lambda:{
        "members":{"GEM":{"rows":[{"ticker":"SRRK","id":"APPLICATION|SRRK|A"},
                                {"ticker":"SRRK","id":"APPLICATION|SRRK|B"}]},
                   "GEM_JR":{"rows":[{"ticker":"CAPR","id":"APPLICATION|CAPR|C"}]}}})
    calls=[]
    def fake(ticker,feed="sip"):
        calls.append((ticker,feed))
        return {"ticker":ticker,"provider":"ALPACA","status":"OK",
                "technicalScreen":"WATCH","noPositionOrTradingAccess":True}
    monkeypatch.setattr(alpaca_trial_selection,"for_ticker",fake)
    client=TestClient(main.app)
    assert client.get("/api/trial-market/GEM/SRRK").status_code==401
    headers={"x-pdufa-internal-key":"test-trial-only"}
    r=client.get("/api/trial-market/GEM/SRRK",headers=headers)
    assert r.status_code==200 and r.json()["ticker"]=="SRRK"
    assert calls==[("SRRK","sip")]
    assert client.get("/api/trial-market/GEM/CAPR",headers=headers).status_code==404
    assert client.get("/api/trial-market/GEM_JR/CAPR?feed=iex",headers=headers).status_code==200
    assert calls[-1]==("CAPR","iex")
    assert client.get("/api/trial-market/PIPELINE/SRRK",headers=headers).status_code==422
    assert client.get("/api/trial-market/GEM/SRRK?feed=xyz",headers=headers).status_code==422


def test_readonly_source_fallback_omits_permanent_ids_without_database(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY","test-source-only")
    monkeypatch.setattr("app.source_workspace.workspace",lambda:{
        "mode":"LIVE_READ_ONLY_GITHUB_SOURCE","asOf":"2026-10-18",
        "disclaimer":"Source research", "pipeline":[{"id":"X","programId":"PDUFA-000888"}],
        "members":{"GEM":{"rows":[{"ticker":"SRRK","id":"A","programId":"PDUFA-000777"}],
                          "history":[]},
                   "GEM_JR":{"rows":[],"history":[]}}})
    client=TestClient(main.app)
    headers={"x-pdufa-internal-key":"test-source-only"}
    result=client.get("/api/trial-source-workspace",headers=headers)
    assert result.status_code==200
    body=result.json()
    assert body["degradedReadOnly"] is True
    assert body["pipeline"][0].get("programId") is None
    assert body["members"]["GEM"]["rows"][0].get("programId") is None
    assert body["members"]["GEM"]["rows"][0]["id"]=="A"


def test_unavailable_market_data_is_never_buy(monkeypatch):
    monkeypatch.setattr(alpaca_trial_selection,"session_context",lambda now:{
        "expectedSession":"2026-10-16",
        "recentSessions":[r["date"] for r in sample()[-61:]]})
    def broken(*args,**kwargs):
        raise ValueError("no source")
    monkeypatch.setattr(alpaca_trial_selection,"_get_daily",broken)
    alpaca_trial_selection._CACHE.clear()
    report=alpaca_trial_selection.for_ticker("SRRK","sip",
        now=datetime(2026,10,18,tzinfo=timezone.utc))
    assert report["status"]=="UNAVAILABLE"
    assert "technicalScreen" not in report
