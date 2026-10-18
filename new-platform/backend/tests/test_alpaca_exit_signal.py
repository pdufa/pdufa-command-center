"""Paper-only Alpaca STAY/EXIT, source gates and data freshness."""
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from urllib.error import HTTPError
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import main, alpaca_exit_signal as module


def bars():
    ds=[]
    d=date(2026,7,1)
    while len(ds)<72:
        if d.weekday()<5:
            n=len(ds);px=20+0.02*n
            ds.append(dict(date=d.isoformat(),close=px,open=px,
                           high=px+.15,low=px-.15,volume=100000,vwap=px))
        d+=timedelta(days=1)
    return ds


def test_paper_position_http_get_and_scrubs_account_id(monkeypatch):
    captured=[]
    def fake(req,timeout):
        captured.append((req.get_method(),req.full_url,timeout))
        return BytesIO(b'{"symbol":"ABCD","qty":"2","avg_entry_price":"22.75","account_id":"private"}')
    monkeypatch.setattr(module,"urlopen",fake)
    monkeypatch.setattr(module,"_credentials",lambda:("api","secret"))
    result=module.paper_position("ABCD")
    assert result=={"exists":True,"avgEntry":22.75,"scope":"ALPACA_PAPER_ONLY"}
    assert captured[0][0]=="GET"
    assert "/positions/ABCD" in captured[0][1]


def test_missing_paper_position_is_wait_not_hold(monkeypatch):
    class Missing(Exception):pass
    def fake(req,timeout):
        raise HTTPError(req.full_url,404,"not held",None,None)
    monkeypatch.setattr(module,"urlopen",fake)
    monkeypatch.setattr(module,"_credentials",lambda:("api","secret"))
    assert module.paper_position("ABCD") is None


def test_technical_two_sma_closes_and_staleness():
    rows=bars()
    recent=[r["date"] for r in rows[-61:]]
    healthy=module.technical_exit(rows,recent)
    assert healthy["belowSma20TwoCloses"] is False
    rows[-2]["close"]-=3
    rows[-1]["close"]-=3
    weak=module.technical_exit(rows,recent)
    assert weak["belowSma20TwoCloses"] is True
    assert weak["trailingStop"]=="UNAVAILABLE_WITHOUT_DATED_ENTRY_AND_STOP_LEDGER"
    try:
        module.technical_exit(rows,recent[:-1])
    except ValueError:
        pass
    else:
        assert False,"stale series must block"


def fake_workspace():
    return {"members":{"GEM":{"rows":[{"id":"APPLICATION|ABCD|D","ticker":"ABCD",
                                      "eventKey":"ABCD|D","pdufaDate":"2026-11-20"}]}}}


def test_exit_rule_and_program_identity(monkeypatch):
    monkeypatch.setattr("app.source_workspace.workspace",fake_workspace)
    monkeypatch.setattr("app.wt_research._context",lambda:{"events":{"ABCD|D":{
        "pdufa_date":"2026-11-20",
        "pdufa_confirmation":"VERIFIED",
        "pdufa_evidence_url":"https://www.fda.gov/sample",
        "outcome":"PENDING",
    }}})
    monkeypatch.setattr(module,"paper_position",lambda ticker:{"exists":True,"avgEntry":19.5})
    today=datetime(2026,10,18,12,tzinfo=timezone.utc)
    rows=bars()
    recent=[r["date"] for r in rows[-61:]]
    monkeypatch.setattr(module,"session_context",lambda now:{
        "expectedSession":rows[-1]["date"],"recentSessions":recent})
    monkeypatch.setattr(module,"history",lambda *args:rows)
    # Use specific clock during a real window, with a clean moving average.
    result=module.exit_for_program("APPLICATION|ABCD|D","ABCD",now=today)
    assert result["status"]=="STAY"
    assert result["technical"]["sma20"]>0
    assert result["readOnly"] and not result["orderExecutionEnabled"]
    rows[-2]["close"]-=3;rows[-1]["close"]-=3
    result=module.exit_for_program("APPLICATION|ABCD|D","ABCD",now=today)
    assert result["status"]=="EXIT_WARNING"
    assert result["reason"]=="TWO_CLOSES_BELOW_SMA20"
    wrong=module.exit_for_program("APPLICATION|ABCD|OTHER","ABCD",now=today)
    assert wrong["status"]=="UNAVAILABLE"
    monkeypatch.setattr(module,"paper_position",lambda ticker:None)
    assert module.exit_for_program("APPLICATION|ABCD|D","ABCD",now=today)["status"]=="WAIT"


def test_exit_endpoint_protected_and_server_identity(monkeypatch):
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY","test-only-api-key")
    main.app.dependency_overrides[main.require_storage]=lambda:None
    captured=[]
    class Session:
        def __init__(self,*args):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def get(self,model,number):
            return SimpleNamespace(ticker="ABCD",source_key="APPLICATION|ABCD|D") if number==1 else None
    monkeypatch.setattr(main,"Session",Session)
    monkeypatch.setattr(module,"exit_for_program",lambda k,t:captured.append((k,t)) or
                        {"ticker":t,"status":"WAIT","reason":"NO_ALPACA_PAPER_POSITION"})
    cli=TestClient(main.app)
    try:
        assert cli.get("/api/exit-signal/PDUFA-000001").status_code==401
        headers={"x-pdufa-internal-key":"test-only-api-key"}
        r=cli.get("/api/exit-signal/PDUFA-000001?ticker=WRONG",headers=headers)
        assert r.status_code==200 and r.json()["ticker"]=="ABCD"
        assert captured==[("APPLICATION|ABCD|D","ABCD")]
        assert cli.get("/api/exit-signal/PDUFA-000002",headers=headers).status_code==404
        assert cli.get("/api/exit-signal/BAD",headers=headers).status_code==422
    finally:
        main.app.dependency_overrides.pop(main.require_storage,None)
