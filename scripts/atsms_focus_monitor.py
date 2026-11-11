#!/usr/bin/env python3
"""ATSMS read-only FOCUS market-hours research worker.

Runs against the canonical, post-POOL FOCUS source roster. Uses Alpaca market
DATA only; no brokerage client, trading URL, order placement or approvals.
Current eight-criterion BUY_SETUP model is unbacktested. The free IEX feed is
partial exchange coverage and may have no extended-hours trades.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, time as dt_time, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
REPORT = ROOT / "reports/atsms/latest.json"
STATE = Path(os.environ.get("ATSMS_STATE_FILE", "/tmp/atsms-focus-signal-state.json"))
ET = ZoneInfo("America/New_York")
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,12}$")
NCT = re.compile(r"^NCT[0-9]{8}$")
API = "https://data.alpaca.markets"
MAX_DATA_BYTES = 6_000_000
MODEL = "WT_EOD_TECHNICAL_V1_UNBACKTESTED"
DISCLAIMER = "Read-only technical research, not validated trade advice or FDA prediction. No broker orders."

def utc_now():
    return datetime.now(timezone.utc)

def snapshot_roster(file=ROSTER, now=None):
    now = now or utc_now()
    source = json.loads(Path(file).read_text(encoding="utf-8"))
    if source.get("schemaVersion") != 1 or not isinstance(source.get("records"), list) or not source["records"]:
        raise ValueError("Missing canonical FOCUS source roster")
    recorded = date.fromisoformat(source["asOf"])
    age = (now.astimezone(ET).date() - recorded).days
    if age < 0 or age > 7:
        raise ValueError("FOCUS roster stale/future (asOf: "+source["asOf"]+")")
    seen, records = set(), []
    for row in source["records"]:
        ticker, nct = row.get("ticker"), row.get("nct")
        if not isinstance(ticker, str) or not SYMBOL.fullmatch(ticker) or not isinstance(nct, str) or not NCT.fullmatch(nct) or nct in seen:
            raise ValueError("FOCUS exact ticker/NCT identity missing, duplicated or invalid")
        seen.add(nct)
        records.append({"ticker":ticker,"nct":nct,"pdufa":row.get("recordedPdufaDate")})
    return records, source["asOf"]

def market_context(now, calendar=None):
    """True NYSE session date and early-close-aware PRE / REGULAR / POST hours."""
    if now.tzinfo is None:
        raise ValueError("UTC-aware clock required")
    local = now.astimezone(ET)
    if not dt_time(4) <= local.time().replace(tzinfo=None) < dt_time(20):
        return None
    if calendar is None:
        import exchange_calendars
        calendar = exchange_calendars.get_calendar("XNYS")
    session = local.date().isoformat()
    if not calendar.is_session(session):
        return None
    close = calendar.session_close(session).to_pydatetime().astimezone(ET)
    if local.time() < dt_time(9, 30):
        stage = "PREMARKET"
    elif now < close.astimezone(timezone.utc):
        stage = "REGULAR"
    else:
        stage = "AFTERHOURS"
    completed = calendar.previous_session(session)
    if now >= close.astimezone(timezone.utc) + timedelta(minutes=20):
        completed = calendar.date_to_session(session)
    expected_day = completed.date().isoformat()
    return {"session":stage,"localDay":session,"expectedCompletedDay":expected_day,
            "openET":"04:00","closeET":"20:00","regularCloseET":close.isoformat()}

def _credentials():
    key = os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID")
    secret = os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY")
    return (key.strip(),secret.strip()) if key and secret and not key.startswith("YOUR_") and not secret.startswith("YOUR_") else None

def _get_json(path, params, keys, fetch=None):
    if fetch is not None:
        return fetch(path, params)
    url = API + path + "?" + urlencode(params)
    req = Request(url, headers={"APCA-API-KEY-ID":keys[0],
        "APCA-API-SECRET-KEY":keys[1],"Accept":"application/json",
        "User-Agent":"PDUFA-ATSMS-ReadOnly-1.0"})
    with urlopen(req, timeout=18) as response:
        content = response.read(MAX_DATA_BYTES + 1)
        if len(content) > MAX_DATA_BYTES:
            raise ValueError("Alpaca response too large")
        return json.loads(content)

def collect_market(symbols, context, now, keys, fetch=None, feed="iex"):
    """Two batch requests, not one API request per NCT or ticker."""
    if not symbols or len(symbols)>120 or feed not in ("iex","sip"):
        raise ValueError("Unsupported ticker batch/feed")
    expected = context["expectedCompletedDay"]
    start = (date.fromisoformat(expected)-timedelta(days=215)).isoformat()
    requested = ",".join(symbols)
    history = _get_json("/v2/stocks/bars",
        {"symbols":requested,"timeframe":"1Day","start":start,
         "end":(date.fromisoformat(expected)+timedelta(days=1)).isoformat(),
         "feed":feed,"adjustment":"raw","sort":"asc","limit":10000},keys,fetch)
    if history.get("next_page_token") or not isinstance(history.get("bars"),dict):
        raise ValueError("Alpaca daily history is truncated/unavailable")
    minute = _get_json("/v2/stocks/bars/latest",{"symbols":requested,"feed":feed},keys,fetch)
    if not isinstance(minute.get("bars"),dict):
        raise ValueError("Alpaca intraday latest bars unavailable")
    result = {}
    for ticker in symbols:
        daily=[]
        for bar in history["bars"].get(ticker,[]):
            try:
                day=datetime.fromisoformat(bar["t"].replace("Z","+00:00")).date().isoformat()
                if day > expected: continue
                o,h,l,c,v=(float(bar[k]) for k in ("o","h","l","c","v"))
                if not all(math.isfinite(x) for x in (o,h,l,c,v)) or min(o,h,l,c)<=0 or v<0 or h<max(o,l,c) or l>min(o,h,c):
                    continue
                daily.append({"date":day,"open":o,"high":h,"low":l,"close":c,"volume":v})
            except (KeyError,TypeError,ValueError,OverflowError):
                continue
        daily.sort(key=lambda x:x["date"])
        if len(set(x["date"] for x in daily)) != len(daily):
            daily = []
        raw = minute["bars"].get(ticker)
        intraday = None
        if isinstance(raw,dict):
            try:
                timestamp=datetime.fromisoformat(raw["t"].replace("Z","+00:00"))
                p,v=float(raw["c"]),float(raw["v"])
                age=(now-timestamp).total_seconds()
                if timestamp.tzinfo is not None and 0 <= age <= 600 and math.isfinite(p) and p>0 and math.isfinite(v) and v>=0:
                    if timestamp.astimezone(ET).date().isoformat()==context["localDay"]:
                        intraday={"close":p,"volume":v,"asOf":timestamp.isoformat(),"feed":feed.upper(),"ageSeconds":int(age)}
            except (KeyError,TypeError,ValueError,OverflowError):
                pass
        result[ticker]={"bars":daily,"minute":intraday}
    return result

def _sma(bars, count):
    return sum(b["close"] for b in bars[-count:])/count

def calculate_metrics(bars, expected):
    """Matches the eight WT EOD screening thresholds; excludes incomplete bars."""
    if len(bars)<61 or bars[-1]["date"]!=expected:
        return None
    if any(a["date"]>=b["date"] for a,b in zip(bars,bars[1:])):
        return None
    last=bars[-1]; prior=bars[-2]
    sma20=_sma(bars,20); sma50=_sma(bars,50); prev_sma20=_sma(bars[:-1],20)
    changes=[b["close"]-a["close"] for a,b in zip(bars,bars[1:])]
    gain=sum(max(0,x) for x in changes[:14])/14
    loss=sum(max(0,-x) for x in changes[:14])/14
    for x in changes[14:]:
        gain=(gain*13+max(0,x))/14
        loss=(loss*13+max(0,-x))/14
    rsi=50 if loss==0 and gain==0 else 100 if loss==0 else 100-100/(1+gain/loss)
    ranges=[max(b["high"]-b["low"],abs(b["high"]-a["close"]),abs(b["low"]-a["close"])) for a,b in zip(bars,bars[1:])]
    atr=sum(ranges[:14])/14
    for x in ranges[14:]: atr=(atr*13+x)/14
    base=bars[-11:-1]
    base_high=max(b["high"] for b in base)
    base_low=min(b["low"] for b in base)
    older_low=min(b["low"] for b in base[:5])
    recent_low=min(b["low"] for b in base[-5:])
    volume20=sum(b["volume"] for b in bars[-21:-1])/20
    if volume20<=0 or atr<=0: return None
    rvol=last["volume"]/volume20
    dollar20=sum(b["close"]*b["volume"] for b in bars[-20:])/20
    trigger=base_high+0.10*atr
    checks=[
        ("BASE","10-session base",base_high-base_low,3*atr,(base_high-base_low)<=3*atr),
        ("LOWS","Stabilizing lows",recent_low,older_low,recent_low>=older_low),
        ("BREAKOUT","Close above 10-session high + ATR buffer",last["close"],trigger,last["close"]>trigger),
        ("TREND","Close > SMA20 > SMA50",last["close"],sma20,last["close"]>sma20>sma50),
        ("RVOL","Relative volume >= 1.5",rvol,1.5,rvol>=1.5),
        ("RSI","RSI14 50–70",rsi,50,50<=rsi<=70),
        ("LIQUIDITY","Average dollar volume >= $1M",dollar20,1_000_000,dollar20>=1_000_000),
        ("ATR","ATR / close <= 10%",atr/last["close"],0.10,atr/last["close"]<=0.10),
    ]
    return {"model":MODEL,"completedDay":expected,"feedScope":"single-exchange unless entitled SIP",
        "lastClose":round(last["close"],4),"sma20":round(sma20,4),"sma50":round(sma50,4),
        "atr14":round(atr,4),"rsi14":round(rsi,2),"rvol20":round(rvol,3),
        "avgDollarVolume20":round(dollar20,2),
        "baseLow":round(base_low,4),"baseHigh":round(base_high,4),
        "entryReference":round(trigger,4),"riskStopReference":round(base_low-.25*atr,4),
        "twoClosesBelowSma20":bool(prior["close"]<prev_sma20 and last["close"]<sma20),
        "checks":[{"code":k,"label":lab,"actual":round(actual,5),
            "threshold":round(limit,5),"pass":bool(ok)} for k,lab,actual,limit,ok in checks],
        "passed":sum(ok for *_,ok in checks),"total":8,
        "technical":"BUY_SETUP" if all(ok for *_,ok in checks) else "WAIT"}

def pdufa_gate(record, now):
    raw=record.get("pdufa")
    if not isinstance(raw,str):
        return {"status":"UNVERIFIED","days":None}
    try:
        day=date.fromisoformat(raw)
    except ValueError:
        return {"status":"UNVERIFIED","days":None}
    days=(day-now.astimezone(ET).date()).days
    return {"status":"PAST" if days<0 else "BLACKOUT" if days<=14 else "CLEAR","days":days}

def study_record(record, market, now):
    date_gate=pdufa_gate(record,now)
    metrics=market.get("metrics")
    minute=market.get("minute")
    result={"ticker":record["ticker"],"nct":record["nct"],
        "reportedPdufa":record["pdufa"],"pdufaGate":date_gate,
        "technical":metrics["technical"] if metrics else "UNAVAILABLE",
        "dailyChecksPassed":metrics["passed"] if metrics else None,
        "intraday":minute,"entry":"UNAVAILABLE","stay":"UNAVAILABLE","exit":"UNAVAILABLE",
        "executionEnabled":False}
    if not metrics: return result
    result["dailyMetrics"]=metrics
    # Exit warnings apply to research watchlists, not verified held positions.
    if metrics["twoClosesBelowSma20"] or (minute and minute["close"]<metrics["baseLow"]) or (
        date_gate["days"] is not None and 0<=date_gate["days"]<=3):
        result["exit"]="RISK_WARNING"
    elif minute: result["exit"]="NO_TRIGGER_OBSERVED"
    if minute:
        p=minute["close"]
        result["stay"]="TREND_INTACT" if p>=metrics["sma20"] and p>=metrics["baseLow"] and metrics["rsi14"]>=45 else "TREND_WEAKENING"
    if date_gate["status"]!="CLEAR":
        result["entry"]="BLOCKED_PDUFA" if date_gate["status"]=="BLACKOUT" else "BLOCKED_UNVERIFIED_OR_PAST"
    elif not minute:
        result["entry"]="UNAVAILABLE_NO_FRESH_INTRADAY_BAR"
    elif metrics["technical"]=="BUY_SETUP" and minute["close"]>=metrics["entryReference"]:
        result["entry"]="TECHNICAL_WATCH_ONLY"
    else:
        result["entry"]="WAIT"
    return result

def _read_state(path):
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        return data if data.get("schemaVersion")==1 and isinstance(data.get("signals"),dict) else None
    except (OSError,ValueError,TypeError):
        return None

def transitions(records, previous):
    old=(previous or {}).get("signals",{})
    current={r["nct"]:{"entry":r["entry"],"exit":r["exit"],"ticker":r["ticker"]} for r in records}
    changes=[]
    if previous is not None:
        for row in records:
            before=old.get(row["nct"])
            if not before: continue
            for category,status in (("entry","TECHNICAL_WATCH_ONLY"),("exit","RISK_WARNING")):
                if row[category]==status and before.get(category)!=status:
                    changes.append({"ticker":row["ticker"],"nct":row["nct"],"event":status})
    return current,changes

def notify_telegram(changes, now):
    token=os.environ.get("TELEGRAM_BOT_TOKEN")
    chat=os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat or not changes: return "NO_DELIVERY" if changes else "NO_CHANGES"
    lines=["ATSMS RESEARCH SIGNAL CHANGE | "+now.astimezone(ET).strftime("%Y-%m-%d %H:%M ET")]
    for change in changes[:20]:
        lines.append(change["ticker"]+" "+change["nct"]+": "+change["event"])
    lines.append("Unbacktested, source-limited; NO trades or broker orders.")
    body=json.dumps({"chat_id":chat,"text":"\n".join(lines)}).encode()
    req=Request("https://api.telegram.org/bot"+token+"/sendMessage",data=body,
        headers={"Content-Type":"application/json"},method="POST")
    try:
        with urlopen(req,timeout=12) as response:
            result=json.load(response)
            return "SENT" if result.get("ok") is True else "FAILED"
    except (OSError,ValueError):
        return "FAILED"

def write_json(path,data):
    dest=Path(path); dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+".tmp")
    tmp.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    tmp.replace(dest)

def run(now=None,roster=ROSTER,report=REPORT,load_market=collect_market,session_override=None):
    now=now or utc_now()
    started=now.isoformat()
    result={"schemaVersion":1,"name":"ATSMS","runAtUTC":started,"marketSession":None,
        "sourceRosterAsOf":None,"focusTrials":0,"uniqueTickers":0,"status":"PENDING",
        "marketFeed":(os.environ.get("ALPACA_DATA_FEED") or "iex").lower(),
        "trials":[],"changes":[],"alerts":"NO_CHANGES",
        "risk":DISCLAIMER,"websiteLiveStatusPublished":False,"brokerOrdersEnabled":False}
    try:
        roster_records,asof=snapshot_roster(roster,now)
        result["sourceRosterAsOf"]=asof
        result["focusTrials"]=len(roster_records)
        symbols=sorted({r["ticker"] for r in roster_records})
        result["uniqueTickers"]=len(symbols)
        session=session_override if session_override is not None else market_context(now)
        if session is None:
            result["status"]="OUTSIDE_EXCHANGE_SESSION"
            return result
        result["marketSession"]=session
        keys=_credentials()
        if not keys:
            result["status"]="ALPACA_CREDENTIALS_NOT_CONFIGURED"
            result["trials"]=[study_record(row,{},now) for row in roster_records]
            return result
        feed=result["marketFeed"]
        if feed not in ("iex","sip"):
            raise ValueError("Unsupported Alpaca feed")
        market=load_market(symbols,session,now,keys,feed=feed)
        for symbol in symbols:
            values=market.get(symbol) or {}
            values["metrics"]=calculate_metrics(values.get("bars") or [],session["expectedCompletedDay"])
            market[symbol]=values
        results=[study_record(row,market.get(row["ticker"]) or {},now) for row in roster_records]
        result["trials"]=results
        result["availableDaily"]=sum(r["dailyChecksPassed"] is not None for r in results)
        result["availableIntraday"]=sum(r["intraday"] is not None for r in results)
        result["status"]="EVALUATED" if result["availableDaily"] else "ALPACA_DATA_UNAVAILABLE"
        if result["availableDaily"]:
            prior=_read_state(STATE)
            current,changed=transitions(results,prior)
            result["changes"]=changed
            result["alerts"]=notify_telegram(changed,now)
            if not changed or result["alerts"]=="SENT":
                write_json(STATE,{"schemaVersion":1,"signals":current,"runAtUTC":started})
        return result
    except HTTPError as e:
        if e.code in (401,403):
            result["status"]="ALPACA_AUTH_REJECTED"
            result["error"]="Alpaca market-data authentication was refused (HTTP "+str(e.code)+"). Verify the GitHub Actions APCA_API_KEY_ID / APCA_API_SECRET_KEY repository secrets; credentials on Render are separate."
        elif e.code == 429:
            result["status"]="ALPACA_RATE_LIMITED"
            result["error"]="Alpaca market-data requests were rate limited (HTTP 429); no technical signals were produced."
        else:
            result["status"]="ALPACA_HTTP_ERROR"
            result["error"]="Alpaca market-data endpoint returned HTTP "+str(e.code)+". No technical signals were produced."
        return result
    except Exception as e:
        result["status"]="SOURCE_OR_CALENDAR_FAILURE"
        result["error"]=type(e).__name__+": "+str(e)[:250]
        return result
    finally:
        # Caller's wrapper saves the report even if no session/trades/data.
        pass

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",type=Path,default=REPORT)
    parser.add_argument("--roster",type=Path,default=ROSTER)
    args=parser.parse_args()
    report=run(roster=args.roster,report=args.report)
    write_json(args.report,report)
    summary=(f"ATSMS {report['status']}: {report['focusTrials']} FOCUS NCTs, "
        f"{report['uniqueTickers']} tickers, "
        f"{report.get('availableDaily',0)} daily metrics and "
        f"{report.get('availableIntraday',0)} fresh minute bars")
    print(summary,flush=True)
    if report.get("error"):
        print("ATSMS BLOCKER: "+report["error"],flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"],"a",encoding="utf-8") as out:
            out.write("## ATSMS read-only research monitor\n\n"+summary+"\n\n")
            out.write("**Market:** "+str((report.get("marketSession") or {}).get("session","CLOSED"))+"  ")
            out.write("**Alerts:** "+report.get("alerts","NO_CHANGES")+"  ")
            out.write("**Orders:** DISABLED\n\n")
            out.write("Only a workflow artifact is published; WT live-status integration is not yet connected.\n")
    return 0 if report["status"] in ("EVALUATED","OUTSIDE_EXCHANGE_SESSION",
        "ALPACA_DATA_UNAVAILABLE","ALPACA_CREDENTIALS_NOT_CONFIGURED") else 1

if __name__=="__main__":
    sys.exit(main())
