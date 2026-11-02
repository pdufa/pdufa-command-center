#!/usr/bin/env python3
"""2016-2025 PDUFA timing study. Research-only; all unknowns are explicit."""
import csv, io, json, os, re, time, warnings
from pathlib import Path
from collections import Counter
from datetime import date
import numpy as np
import pandas as pd
import requests
warnings.filterwarnings("ignore", category=FutureWarning)
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"research_outputs"/"pdufa_ten_year"
OUT.mkdir(parents=True,exist_ok=True)
YEAR1,YEAR2=2016,2025
s=requests.Session()
s.headers.update({"User-Agent":"PDUFA Historical Research academic non-commercial research@example.org"})
audit=[]
def note(message): print(message,flush=True);audit.append(message)
def get_archive():
    url="https://raw.githubusercontent.com/ejeej/EventsStockPrices/main/EventsStockPricesApp/Events.xlsx"
    try:
        r=s.get(url,timeout=35);r.raise_for_status()
        sheets=pd.read_excel(io.BytesIO(r.content),sheet_name=None)
        note("External archive sheets: "+str({k:{"count":len(v),"columns":list(v.columns)} for k,v in sheets.items()})[:2000])
        return sheets
    except Exception as e:
        note("External 2017-2022 archive unavailable: "+str(e)[:300]);return {}
def detect(df):
    cols={str(x).lower().replace("_"," ").strip():x for x in df.columns}
    def find(*words):
        for c,real in cols.items():
            if any(w in c for w in words):return real
        return None
    return find("ticker","symbol"),find("date"),find("event","type","catalyst","description","status")
def get_events():
    rows=[]
    path=ROOT/"data"/"fda_v3_historical_backtest.csv"
    if path.exists():
        df=pd.read_csv(path,low_memory=False)
        for _,x in df.iterrows():
            sym=str(x.get("ticker","")).strip().upper()
            dt=pd.to_datetime(x.get("pdufa_date"),errors="coerce")
            if pd.notna(dt) and YEAR1<=dt.year<=YEAR2 and re.fullmatch(r"[A-Z]{1,6}",sym):
                rows.append({"ticker":sym,"pdufa_date":dt.date().isoformat(),"event_source":"project_fda_v3","date_status":"UNVERIFIED_PREDECISION_DISCLOSURE"})
    phase3={}
    for name,df in get_archive().items():
        tick,dt,cat=detect(df)
        if not all([tick,dt,cat]):continue
        for _,x in df.iterrows():
            t=str(x[tick]).upper().strip()
            # Ignore multi-ticker descriptions and empty tickers
            if not re.fullmatch(r"[A-Z]{1,6}",t):continue
            try: day=pd.to_datetime(x[dt],errors="coerce")
            except:continue
            if pd.isna(day):continue
            kind=str(x[cat]).upper()
            if ("PDUFA" in kind and YEAR1<=day.year<=YEAR2):
                rows.append({"ticker":t,"pdufa_date":day.date().isoformat(),"event_source":"public_2017_2022_archive","date_status":"THIRD_PARTY_DATE_VERIFY"})
            if "PHASE 3" in kind or "PHASE III" in kind:
                phase3.setdefault(t,[]).append(day.date())
    events=pd.DataFrame(rows)
    if events.empty:
        return pd.DataFrame(columns=["ticker","pdufa_date","event_source","date_status","phase3_date"]),phase3
    events=events.sort_values("event_source").drop_duplicates(["ticker","pdufa_date"]).sort_values("pdufa_date")
    events["phase3_date"]=events.apply(lambda x:max((d for d in phase3.get(x.ticker,[]) if d<date.fromisoformat(x.pdufa_date)),default=None),axis=1)
    return events,phase3
def get_prices(symbol):
    # Yahoo first, then Stooq. Never infer prices from sources lacking history.
    start="2015-01-01";end="2026-01-10"
    try:
        import yfinance as yf
        frame=yf.download(symbol,start=start,end=end,auto_adjust=True,progress=False,threads=False,timeout=14)
        if isinstance(frame.columns,pd.MultiIndex):frame.columns=frame.columns.get_level_values(0)
        if not frame.empty and "Close" in frame:
            a=frame["Close"].dropna()
            if len(a)>20:return a.rename("close"),"YAHOO_AUTOADJUST"
    except Exception as e:note("Yahoo failure "+symbol+" "+str(e)[:100])
    try:
        url="https://stooq.com/q/d/l/"
        resp=s.get(url,params={"s":symbol.lower()+".us","i":"d","d1":"20150101","d2":"20260110"},timeout=18)
        if resp.status_code==200 and resp.text.startswith("Date,Open"):
            frame=pd.read_csv(io.StringIO(resp.text),parse_dates=["Date"])
            a=frame.set_index("Date")["Close"].sort_index().astype(float)
            if len(a)>20:return a.rename("close"),"STOOQ_SPLIT_ADJUSTMENT_UNCONFIRMED"
    except Exception as e:note("Stooq failure "+symbol+" "+str(e)[:100])
    return pd.Series(dtype=float),"MISSING_PRICE"
def get_shares(symbol):
    try:
        import yfinance as yf
        a=yf.Ticker(symbol).get_shares_full(start="2015-01-01",end="2026-01-10")
        if a is not None and len(a):
            a.index=pd.to_datetime(a.index).tz_localize(None) if a.index.tz is None else pd.to_datetime(a.index).tz_convert(None)
            return a.sort_index()
    except Exception as e:note("Historical shares unavailable "+symbol+" "+str(e)[:80])
    return pd.Series(dtype=float)
def session_cap(price,shares,entry):
    if shares.empty:return None
    older=shares[shares.index<=entry]
    if older.empty:return None
    stamp=older.index[-1]
    if (entry-stamp).days>365:return None
    amount=float(older.iloc[-1])
    if not 1e5<amount<1e11:return None
    return amount*price
def run():
    events,phase3=get_events()
    note("Unique PDUFA event candidates="+str(len(events))+" ; years="+str(events.pdufa_date.str[:4].value_counts().sort_index().to_dict()))
    memo={}
    historical=[]
    all_candidates=[]
    for _,r in events.iterrows():
        ticker=r.ticker
        if ticker not in memo:memo[ticker]=get_prices(ticker),get_shares(ticker)
        stock,source=memo[ticker]
        event=pd.Timestamp(r.pdufa_date)
        before=stock[stock.index.normalize()<event] if not stock.empty else stock
        rec=dict(r)
        rec.update({"stock_price_source":source,"predecision_sessions":len(before),"cap_at_T90":None,"phase3_known":bool(r.phase3_date),"eligible_marketcap_at_T90":False,"reason":""})
        if len(before)<90:
            rec["reason"]="LESS_THAN_90_PREDECISION_SESSIONS";all_candidates.append(rec);continue
        shares=memo[ticker][1]
        cap=session_cap(float(before.iloc[-90]),shares,before.index[-90])
        rec["cap_at_T90"]=cap
        rec["eligible_marketcap_at_T90"]=cap is not None and 3e8<=cap<=1e10
        if cap is None:
            rec["reason"]="NO_HISTORICAL_SHARES_CAP";all_candidates.append(rec);continue
        if not rec["eligible_marketcap_at_T90"]:
            rec["reason"]="OUTSIDE_300M_10B_AT_T90";all_candidates.append(rec);continue
        if not r.phase3_date:
            rec["reason"]="PHASE3_READOUT_UNVERIFIED";all_candidates.append(rec);continue
        # No trade before next session after publicly reported Phase 3 catalyst.
        allowed=before[before.index.date>r.phase3_date]
        if len(allowed)<2:
            rec["reason"]="NO_POST_PHASE3_TRADABLE_SESSIONS";all_candidates.append(rec);continue
        rec["reason"]="PILOT_ELIGIBLE_DATE_STILL_NEEDS_PRIMARY_VERIFICATION"
        rec["admissible_start"]=allowed.index[0].date().isoformat()
        rec["Tminus3"]=before.index[-3].date().isoformat()
        all_candidates.append(rec)
        # Record all 5-87-session windows, with fixed T-90 .. T-3 definitions.
        for entry in range(90,7,-1):
            a=before.iloc[-entry]
            at=before.index[-entry]
            if at.date()<=r.phase3_date:continue
            entry_cap=session_cap(float(a),shares,at)
            if entry_cap is None or not 3e8<=entry_cap<=1e10:continue
            for exit in range(entry-5,2,-1):
                b=before.iloc[-exit]
                historical.append({"event_key":ticker+"|"+r.pdufa_date,"ticker":ticker,"pdufa_year":event.year,"entry_Tminus":entry,"exit_Tminus":exit,"return_pct":100*(float(b)/float(a)-1),"market_cap_at_entry":entry_cap,"price_source":source,"date_status":r.date_status})
        if len(all_candidates)%25==0:note("Progress: "+str(len(all_candidates))+" event candidates")
    pd.DataFrame(all_candidates).to_csv(OUT/"event_coverage.csv",index=False)
    trades=pd.DataFrame(historical)
    if trades.empty:
        summary={"status":"NOT_VALIDATED_NO_COMPLETE_ELIGIBLE_COHORT","unique_event_candidates":len(events),"marketcap_eligible_and_phase3_known":sum(z.get("reason","").startswith("PILOT_") for z in all_candidates),"price_feeds":dict(Counter(v[0][1] for v in memo.values())),"years_in_events":events.pdufa_date.str[:4].value_counts().sort_index().to_dict(),"missing_2016":not any(events.pdufa_date.str.startswith("2016")),"top_windows":[]}
    else:
        trades.to_csv(OUT/"trade_candidates.csv",index=False)
        group=trades.groupby(["entry_Tminus","exit_Tminus"])["return_pct"]
        rank=group.agg(["median","mean","count",lambda x:sum(x>0)]).reset_index()
        rank.columns=["entry_Tminus","exit_Tminus","median_pct","mean_pct","n_events","n_positive"]
        rank=rank[rank.n_events>=10].sort_values("median_pct",ascending=False)
        rank.to_csv(OUT/"window_rankings_in_sample.csv",index=False)
        summary={"status":"PRELIMINARY_ONLY_PENDING_PRIMARY_DATE_AND_EVENT_VERIFICATION","unique_event_candidates":len(events),"years_in_events":events.pdufa_date.str[:4].value_counts().sort_index().to_dict(),"price_feeds":dict(Counter(v[0][1] for v in memo.values())),"strict_phase3_cap_events":len(trades.event_key.unique()),"top_windows":rank.head(10).to_dict("records"),"train_years":"2016-2022","holdout_years":"2023-2025","warning":"Full independent 10-year validation requires original historical PDUFA dates, point-in-time shares and complete delisted coverage."}
        train=trades[trades.pdufa_year<=2022]
        hold=trades[trades.pdufa_year>=2023]
        if train.event_key.nunique()>=20 and hold.event_key.nunique()>=20:
            grid=train.groupby(["entry_Tminus","exit_Tminus"]).return_pct.agg(["median","count"]).reset_index()
            grid=grid[grid["count"]>=20].sort_values("median",ascending=False)
            if not grid.empty:
                e,z=int(grid.iloc[0].entry_Tminus),int(grid.iloc[0].exit_Tminus)
                h=hold[(hold.entry_Tminus==e)&(hold.exit_Tminus==z)]
                summary["holdout"]={"entry_Tminus":e,"exit_Tminus":z,"training_median":float(grid.iloc[0]["median"]),"holdout_events":h.event_key.nunique(),"holdout_median":float(h.return_pct.median()),"holdout_win_pct":float((h.return_pct>0).mean()*100)}
    # Always explain incomplete data instead of fabricating a result.
    summary["schema"]="2026-11-02 2016-2025 prospective research, no claims of successful forecast"
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,default=str))
    (OUT/"data_quality_log.txt").write_text("\n".join(audit))
    note("FINISHED: "+json.dumps(summary,default=str)[:5000])
if __name__=="__main__":run()
