#!/usr/bin/env python3
import argparse, csv, html, json, re, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
CAND=DATA/"pdufa_candidates.csv"
REG=DATA/"company_registry.csv"
STATUS=DATA/"recheck_status.csv"
UA="PDUFACommandCenter/1.0 pdufa-command-center@users.noreply.github.com"
CATS=["pdufa_date","phase3","financing","cash_runway","market_data","ownership_insiders"]
BASE=["event_key","ticker","company","drug","pdufa_date","run_status","requested_scope","started_at_utc","completed_at_utc","last_successful_recheck_utc","change_count","error_count"]
COLS=BASE+sum(([c+"_status",c+"_note",c+"_source"] for c in CATS),[])

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def s(v):
    if v is None: return ""
    x=str(v).strip()
    return "" if x.lower() in {"nan","none","<na>"} else x

def get(url,timeout=18,accept="*/*"):
    q=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":accept})
    with urllib.request.urlopen(q,timeout=timeout) as r:
        return r.read().decode("utf-8","replace")

def text(raw):
    raw=re.sub(r"(?is)<script.*?</script>|<style.*?</style>"," ",raw or "")
    raw=re.sub(r"(?s)<[^>]+>"," ",raw)
    return re.sub(r"\s+"," ",html.unescape(raw)).strip()

def note(x,n=380):
    x=re.sub(r"\s+"," ",s(x))
    return x if len(x)<=n else x[:n-1].rstrip()+"…"

def is_fda_url(url):
    try:
        host=(urllib.parse.urlparse(s(url)).hostname or "").lower()
    except Exception:
        return False
    return host=="fda.gov" or host.endswith(".fda.gov")

def published_date(raw,plain=""):
    # Prefer publication metadata from the FDA page; this is the posting/action
    # date shown in Streamlit, never the date our recheck happened to run.
    for pat in [
        r'(?i)"datePublished"\s*:\s*"(20\d{2}-\d{2}-\d{2})',
        r'(?i)article:published_time[^>]{0,240}content=["\'](20\d{2}-\d{2}-\d{2})',
        r'(?i)content=["\'](20\d{2}-\d{2}-\d{2})[^"\']*["\'][^>]{0,240}article:published_time',
        r'(?i)"dateModified"\s*:\s*"(20\d{2}-\d{2}-\d{2})',
    ]:
        m=re.search(pat,raw or "")
        if m:
            return m.group(1)
    head=(plain or "")[:1800]
    m=re.search(r"(?i)\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})\b",head)
    if m:
        try:
            return datetime.strptime(m.group(0),"%B %d, %Y").date().isoformat()
        except Exception:
            pass
    return ""

def final_fda_outcome(plain,drug):
    low=(plain or "").lower()
    token=s(drug).lower().split("/")[0].split("(")[0].strip()
    for m in re.finditer(r"\bfda\s+(?:has\s+)?approv(?:es|ed)\b",low):
        window=low[max(0,m.start()-250):m.end()+800]
        if not token or token[:8] in window:
            return "APPROVED"
    for m in re.finditer(r"\bcomplete response letter\b",low):
        window=low[max(0,m.start()-350):m.end()+650]
        if "fda" in window and (not token or token[:8] in window):
            return "CRL"
    return ""

def load(path):
    return pd.read_csv(path,dtype=str,keep_default_na=False)

def status_frame(c):
    old=load(STATUS) if STATUS.exists() else pd.DataFrame(columns=COLS)
    for k in COLS:
        if k not in old: old[k]=""
    old=old[COLS].drop_duplicates("event_key",keep="last")
    base=c[["event_key","ticker","company","drug","pdufa_date"]]
    out=base.merge(old.drop(columns=["ticker","company","drug","pdufa_date"],errors="ignore"),on="event_key",how="left",validate="one_to_one")
    for k in COLS:
        if k not in out: out[k]=""
        out[k]=out[k].fillna("").astype(str)
    return out[COLS]

def cik_map():
    r=load(REG)
    return {s(x["ticker"]).upper():s(x["cik10"]) for _,x in r.iterrows()}

def sec_filings(cik,limit=12):
    if not cik: return [],""
    cik=str(cik).zfill(10)
    url="https://data.sec.gov/submissions/CIK"+cik+".json"
    o=json.loads(get(url,accept="application/json"))
    r=(o.get("filings") or {}).get("recent") or {}
    out=[]
    keep={"8-K","10-Q","10-K","S-3","S-3ASR","424B5","424B3","4","3","SC 13D","SC 13D/A","SC 13G","SC 13G/A"}
    for i,f in enumerate(r.get("form") or []):
        if len(out)>=limit: break
        if f not in keep: continue
        a=(r.get("accessionNumber") or [""])[i]; d=(r.get("primaryDocument") or [""])[i]
        fd=(r.get("filingDate") or [""])[i]
        if not a or not d: continue
        u="https://www.sec.gov/Archives/edgar/data/"+str(int(cik))+"/"+a.replace("-","")+"/"+urllib.parse.quote(d)
        out.append({"form":f,"date":fd,"url":u})
    return out,url

def pdufa_check(r):
    u=s(r.get("pdufa_evidence_url")); d=s(r.get("pdufa_date")); drug=s(r.get("drug"))
    if not u:
        return {"status":"NO_VERIFIED_SOURCE","note":"No saved FDA/PDUFA source. Stored date "+(d or "not captured")+" retained; no cross-event fallback used.","source":""}
    if not is_fda_url(u):
        return {"status":"NON_FDA_SOURCE_RETAINED","note":"Saved source is not an FDA domain. It may support the target date, but it cannot automatically close the case or create a DECISION DATE.","source":u}
    try:
        raw=get(u)
        plain=text(raw)
        out=final_fda_outcome(plain,drug)
        if not out:
            return {"status":"FDA_SOURCE_CHECKED_NO_FINAL_DECISION","note":"FDA source reachable; no event-specific final APPROVED/CRL decision safely identified. Stored target "+(d or "not captured")+" remains open.","source":u}
        dd=published_date(raw,plain)
        if not dd:
            return {"status":"FINAL_DECISION_DATE_UNVERIFIED","note":"Final FDA outcome language found, but the FDA posting/action date could not be safely extracted. Case remains open until DECISION DATE is verified.","source":u}
        return {"status":"FINAL_DECISION_VERIFIED","note":"Final FDA "+out+" decision verified with FDA posting/action date "+dd+".","source":u,"outcome":out,"decision_date":dd}
    except Exception as e:
        return {"status":"CHECK_ERROR","note":note("FDA/PDUFA source failed: "+str(e)),"source":u}

def p3_check(r):
    ids=re.findall(r"NCT\d{8}",s(r.get("nct_id")).upper())
    for nct in ids[:3]:
        u="https://clinicaltrials.gov/api/v2/studies/"+nct
        try:
            o=json.loads(get(u,accept="application/json"))
            raw=json.dumps(o,separators=(",",":"))
            vals=re.findall(r'"pValue"\s*:\s*"([^"]+)"',raw)+re.findall(r'"pValue"\s*:\s*([0-9.eE+-]+)',raw)
            vals=list(dict.fromkeys([s(x) for x in vals if s(x)]))[:8]
            if vals: return {"status":"P_VALUE_FOUND","note":nct+": "+" | ".join(vals),"source":u,"pvalues":" | ".join(vals)}
            return {"status":"CHECKED_NO_P_VALUE","note":nct+": record checked; no p-value field safely extracted.","source":u}
        except Exception:
            pass
    u=s(r.get("trial_evidence_url"))
    if u:
        try:
            z=text(get(u)); vals=list(dict.fromkeys(re.findall(r"(?i)\bp\s*(?:=|<|≤)\s*0?\.\d+(?:e-?\d+)?",z)))[:8]
            if vals: return {"status":"P_VALUE_FOUND","note":"Saved trial source: "+" | ".join(vals),"source":u,"pvalues":" | ".join(vals)}
            return {"status":"SOURCE_REACHABLE","note":"Saved trial source checked; no p-value safely extracted.","source":u}
        except Exception as e:
            return {"status":"CHECK_ERROR","note":note("Trial source failed: "+str(e)),"source":u}
    return {"status":"NO_TRIAL_ID","note":"No event-specific NCT ID or trial source available.","source":""}

def financing_check(r,files):
    items=[]
    u=s(r.get("financing_evidence_url"))
    if u: items.append({"form":"saved","url":u})
    items += [x for x in files if x["form"] in {"8-K","424B5","424B3","S-3","S-3ASR","10-Q","10-K"}][:8]
    pats=[r"(?i)closing of (?:the )?.{0,40}offering",r"(?i)(?:offering|financing) (?:was )?completed",r"(?i)(?:we|company) closed .{0,40}(?:offering|financing)"]
    for f in items:
        try: z=text(get(f["url"]))
        except Exception: continue
        for p in pats:
            m=re.search(p,z)
            if m:
                return {"status":"CLOSURE_EVIDENCE_FOUND","note":note(z[max(0,m.start()-100):m.end()+220]),"source":f["url"],"closed":True}
    return {"status":"CHECKED_NO_NEW_CLOSURE" if items else "NO_SOURCE","note":"Financing sources checked; no new closure safely confirmed." if items else "No financing source available.","source":u or (items[0]["url"] if items else "")}

def latest_fact(o,names):
    facts=(o.get("facts") or {}).get("us-gaap") or {}; rows=[]
    for n in names:
        for x in ((facts.get(n) or {}).get("units") or {}).get("USD",[]):
            if x.get("form") in {"10-Q","10-K"} and x.get("val") is not None:
                rows.append((x.get("end",""),x.get("filed",""),float(x["val"]),x))
    return max(rows,default=None,key=lambda x:(x[0],x[1]))

def cash_check(cik):
    if not cik: return {"status":"NO_CIK","note":"No SEC CIK available.","source":""}
    u="https://data.sec.gov/api/xbrl/companyfacts/CIK"+str(cik).zfill(10)+".json"
    try:
        o=json.loads(get(u,accept="application/json"))
        cf=latest_fact(o,["CashAndCashEquivalentsAtCarryingValue","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents","CashAndShortTermInvestments"])
        op=latest_fact(o,["NetCashProvidedByUsedInOperatingActivities"])
        if not cf: return {"status":"CHECKED_NO_CASH_FACT","note":"SEC Companyfacts checked; no current cash fact safely identified.","source":u}
        cash=max(0,cf[2]); runway=None; msg="Latest SEC cash fact USD "+format(cash,",.0f")+" ("+cf[0]+")."
        if op and op[2]<0:
            a=s(op[3].get("start")); b=s(op[3].get("end"))
            try: days=(pd.Timestamp(b)-pd.Timestamp(a)).days
            except Exception: days=0
            if 60<=days<=200:
                burn=-op[2]; monthly=burn/(days/30.4375)
                if monthly>0: runway=cash/monthly; msg+=" Simple runway ~"+format(runway,".1f")+" months."
        return {"status":"RUNWAY_ESTIMATED" if runway is not None else "CASH_UPDATED","note":msg,"source":u,"cash":cash,"runway":runway}
    except Exception as e:
        return {"status":"SOURCE_BLOCKED_RETAINED","note":note("SEC Companyfacts unavailable from worker; retained stored cash/runway values. "+str(e)),"source":u}

def market_check(ticker):
    symbol=s(ticker).upper()
    u="https://query1.finance.yahoo.com/v8/finance/chart/"+urllib.parse.quote(symbol)+"?range=3mo&interval=1d&events=history"
    try:
        o=json.loads(get(u,timeout=18,accept="application/json"))
        result=((o.get("chart") or {}).get("result") or [])
        if result:
            q=((result[0].get("indicators") or {}).get("quote") or [{}])[0]
            closes=q.get("close") or []; vols=q.get("volume") or []; times=result[0].get("timestamp") or []
            g=[(times[i],float(closes[i]),float(vols[i] or 0)) for i in range(min(len(times),len(closes),len(vols))) if closes[i] is not None]
            if g:
                g=g[-35:]; last=g[-1]; vv=[x[2] for x in g[-20:] if x[2]>0]; av=sum(vv)/len(vv) if vv else None
                ret=(last[1]/g[0][1]-1)*100 if len(g)>1 and g[0][1] else None
                d=datetime.fromtimestamp(last[0],timezone.utc).date().isoformat()
                return {"status":"MARKET_UPDATED","note":"Latest public close USD "+format(last[1],".2f")+" on "+d+".","source":u,"price":last[1],"volume":av,"return30":ret}
    except Exception as e:
        yahoo_error=str(e)
    stooq="https://stooq.com/q/d/l/?s="+urllib.parse.quote(s(ticker).lower()+".us")+"&i=d"
    try:
        rows=list(csv.DictReader(get(stooq).splitlines())); g=[]
        for x in rows:
            try:g.append((x["Date"],float(x["Close"]),float(x.get("Volume") or 0)))
            except Exception:pass
        if g:
            g=g[-35:]; last=g[-1]; vv=[x[2] for x in g[-20:] if x[2]>0]; av=sum(vv)/len(vv) if vv else None
            ret=(last[1]/g[0][1]-1)*100 if len(g)>1 and g[0][1] else None
            return {"status":"MARKET_UPDATED","note":"Latest public close USD "+format(last[1],".2f")+" on "+last[0]+".","source":stooq,"price":last[1],"volume":av,"return30":ret}
    except Exception as e:
        stooq_error=str(e)
    return {"status":"SOURCE_UNAVAILABLE","note":"Public market sources returned no usable data; retained stored market values. Yahoo: "+locals().get("yahoo_error","no rows")+"; Stooq: "+locals().get("stooq_error","no rows"),"source":u}

def ownership_check(files,sub):
    own=[x for x in files if x["form"].startswith("SC 13")]; ins=[x for x in files if x["form"] in {"3","4"}]
    allf=sorted(own+ins,key=lambda x:x["date"],reverse=True)
    msg="Recent SEC ownership filings: "+str(len(own))+"; insider Forms 3/4: "+str(len(ins))+"."
    if allf: msg+=" Latest "+allf[0]["form"]+" filed "+allf[0]["date"]+"."
    msg+=" Exchange-listed options activity is not inferred from SEC ownership filings."
    return {"status":"SEC_FILINGS_CHECKED","note":msg,"source":allf[0]["url"] if allf else sub}

def setv(df,i,k,v):
    if v is None or s(v)=="": return 0
    if k not in df: df[k]=""
    nv=(format(v,".6f").rstrip("0").rstrip(".") if isinstance(v,float) else s(v))
    if s(df.at[i,k])==nv:return 0
    df.at[i,k]=nv; return 1

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--event-key",action="append",default=[]); ap.add_argument("--ticker",action="append",default=[])
    ap.add_argument("--all",action="store_true"); ap.add_argument("--categories",default=",".join(CATS)); ap.add_argument("--no-sleep",action="store_true")
    a=ap.parse_args(); c=load(CAND).drop_duplicates("event_key",keep="last").reset_index(drop=True); st=status_frame(c); cm=cik_map()
    cats=[x for x in a.categories.split(",") if x]; bad=[x for x in cats if x not in CATS]
    if bad: raise SystemExit("unknown categories: "+",".join(bad))
    if a.all: ids=list(c.index); scope="ALL"
    else:
        keys={s(x) for x in a.event_key if s(x)}; ticks={s(x).upper() for x in a.ticker if s(x)}
        ids=[i for i,r in c.iterrows() if s(r["event_key"]) in keys or s(r["ticker"]).upper() in ticks]; scope="EVENT" if keys else "TICKER"
        mk=keys-{s(c.at[i,"event_key"]) for i in ids}; mt=ticks-{s(c.at[i,"ticker"]).upper() for i in ids}
        if mk: raise SystemExit("event key not found: "+",".join(sorted(mk)))
        if mt: raise SystemExit("no current PDUFA event for ticker: "+",".join(sorted(mt)))
    if not ids: raise SystemExit("select --all, --event-key, or --ticker")
    total=0; started=now()
    for n,i in enumerate(ids,1):
        r=c.loc[i]; key=s(r["event_key"]); q=st.index[st["event_key"].eq(key)]
        if len(q)!=1: raise SystemExit("status mismatch for "+key)
        j=q[0]; st.at[j,"run_status"]="RUNNING"; st.at[j,"requested_scope"]=scope; st.at[j,"started_at_utc"]=started
        cik=cm.get(s(r["ticker"]).upper(),""); files=[]; sub=""; secerr=""
        if "financing" in cats or "ownership_insiders" in cats:
            try: files,sub=sec_filings(cik)
            except Exception as e: secerr=str(e)
        res={}; ch=0; er=0
        if "pdufa_date" in cats:
            res["pdufa_date"]=pdufa_check(r); out=res["pdufa_date"].get("outcome")
            dd=res["pdufa_date"].get("decision_date")
            if out and dd and (s(r.get("outcome")).upper()!=out or s(r.get("decision_date"))!=dd):
                ch+=setv(c,i,"outcome",out); ch+=setv(c,i,"decision_date",dd); ch+=setv(c,i,"check_status","RESOLVED_"+out)
        if "phase3" in cats:
            res["phase3"]=p3_check(r); pv=res["phase3"].get("pvalues")
            if pv and not s(r.get("reported_p_values")): ch+=setv(c,i,"reported_p_values",pv)
        if "financing" in cats:
            res["financing"]={"status":"SOURCE_BLOCKED_RETAINED","note":"SEC submissions endpoint unavailable from worker; retained existing event financing data. "+secerr,"source":s(r.get("financing_evidence_url"))} if secerr and not s(r.get("financing_evidence_url")) else financing_check(r,files)
            if res["financing"].get("closed") and s(r.get("financing_status")).upper() in {"","UNKNOWN","NOT AVAILABLE","RUNNING","ANNOUNCED"}:
                ch+=setv(c,i,"financing_status","CLOSED"); ch+=setv(c,i,"financing_evidence_url",res["financing"].get("source"))
        if "cash_runway" in cats:
            res["cash_runway"]=cash_check(cik); ch+=setv(c,i,"cash",res["cash_runway"].get("cash")); ch+=setv(c,i,"cash_runway_months",res["cash_runway"].get("runway"))
        if "market_data" in cats:
            res["market_data"]=market_check(r["ticker"]); ch+=setv(c,i,"price_last",res["market_data"].get("price")); ch+=setv(c,i,"avg_volume_20d",res["market_data"].get("volume")); ch+=setv(c,i,"return_30d_pct",res["market_data"].get("return30"))
        if "ownership_insiders" in cats:
            res["ownership_insiders"]={"status":"SOURCE_BLOCKED_RETAINED","note":"SEC submissions endpoint unavailable from worker; no ownership/insider inference made. "+secerr,"source":""} if secerr else ownership_check(files,sub)
        for cat,x in res.items():
            st.at[j,cat+"_status"]=s(x.get("status")); st.at[j,cat+"_note"]=s(x.get("note")); st.at[j,cat+"_source"]=s(x.get("source"))
            if "ERROR" in s(x.get("status")).upper():er+=1
        done=now(); st.at[j,"completed_at_utc"]=done; st.at[j,"change_count"]=str(ch); st.at[j,"error_count"]=str(er)
        st.at[j,"run_status"]="COMPLETED_WITH_ERRORS" if er else "COMPLETED"
        if not er: st.at[j,"last_successful_recheck_utc"]=done
        c.at[i,"last_checked"]=done; total+=ch
        if not a.no_sleep and n<len(ids):time.sleep(.15)
    c.to_csv(CAND,index=False); st.to_csv(STATUS,index=False)
    print(json.dumps({"status":"ok","scope":scope,"events_checked":len(ids),"categories":cats,"candidate_field_changes":total,"completed_at_utc":now()}))

if __name__=="__main__":
    main()
