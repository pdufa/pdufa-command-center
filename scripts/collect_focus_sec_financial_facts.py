#!/usr/bin/env python3
"""Collect dated SEC issuer-level public financial facts for active FOCUS tickers.

Issuer facts do NOT establish trial-product ownership, drug rights, forecast
sales, actual PDUFA probability, treatment prices or investment upside.
Unavailable SEC APIs do not cause guessed zeroes or reset old values.
"""
from __future__ import annotations
import csv,json,os,re,time
from pathlib import Path
from datetime import date,datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
ROSTER=ROOT/"new-platform/frontend/data/p3PostDataActive.json"
REGISTRY=ROOT/"data/company_registry.csv"
OUT=ROOT/"reports/focus-survey"
RESULT=OUT/"sec-companyfacts.json"
SUMMARY=OUT/"sec-companyfacts-summary.json"
AGENT_DEFAULT="PDUFACommandCenterResearch/1.0 (+https://github.com/pdufa/pdufa-command-center/issues)"
CIK=re.compile(r"^[0-9]{10}$")
ALLOWED_FORMS={"10-K","10-K/A","10-Q","10-Q/A","20-F","20-F/A","40-F","40-F/A"}
METRICS={
 "Cash and cash equivalents":[("us-gaap","CashAndCashEquivalentsAtCarryingValue"),
  ("ifrs-full","CashAndCashEquivalents")],
 "Cash, cash equivalents and restricted cash":[
  ("us-gaap","CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")],
 "Revenue":[("us-gaap","RevenueFromContractWithCustomerExcludingAssessedTax"),
  ("us-gaap","Revenues"),("us-gaap","SalesRevenueNet"),("ifrs-full","Revenue")],
 "Operating cash flow":[("us-gaap","NetCashProvidedByUsedInOperatingActivities"),
  ("ifrs-full","CashFlowsFromUsedInOperatingActivities")],
 "Long-term debt":[("us-gaap","LongTermDebtNoncurrent"),
  ("us-gaap","LongTermDebt"),("ifrs-full","NoncurrentBorrowings")],
 "Current debt":[("us-gaap","LongTermDebtCurrent"),
  ("us-gaap","ShortTermBorrowings"),("ifrs-full","CurrentBorrowings")],
 "Shares outstanding":[("dei","EntityCommonStockSharesOutstanding"),
  ("us-gaap","CommonStockSharesOutstanding")],
}
def load(path):
 return json.loads(path.read_text(encoding="utf-8"))
def atomic(path,v):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_suffix(path.suffix+".tmp")
 temp.write_text(json.dumps(v,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 temp.replace(path)
def today():
 return datetime.now(timezone.utc).date().isoformat()
def user_agent():
 u=os.getenv("SEC_USER_AGENT",AGENT_DEFAULT)
 if not 12<=len(u)<=250 or "\n" in u or "\r" in u:
  raise ValueError("INVALID_DECLARED_SEC_RESEARCH_ID")
 return u
def sec_get(url,max_bytes=11_000_000):
 error=None
 for attempt in range(3):
  try:
   req=Request(url,headers={"User-Agent":user_agent(),
      "Accept":"application/json","Accept-Encoding":"gzip, deflate"})
   with urlopen(req,timeout=25) as r:
    if r.geturl()!=url or r.status!=200 or "json" not in r.headers.get("Content-Type","").lower():
     raise ValueError("SEC_INVALID_RESPONSE_OR_REDIRECT")
    raw=r.read(max_bytes+1)
   if len(raw)>max_bytes:raise ValueError("SEC_DOCUMENT_TOO_LARGE")
   return json.loads(raw)
  except HTTPError as e:
   error="SEC_HTTP_"+str(e.code)
   if e.code in (400,401,403,404):break
  except (URLError,TimeoutError,OSError,ValueError) as e:
   error=type(e).__name__+":"+str(e)[:110]
  if attempt<2:time.sleep(1.2*(attempt+1))
 raise RuntimeError(error or "SEC_UNAVAILABLE")
def index():
 allowed=set()
 for r in load(ROSTER)["records"]:
  allowed.add(str(r["ticker"]).upper())
 if not allowed or len(allowed)>100:
  raise ValueError("INVALID_FOCUS_ISSUER_UNIVERSE")
 out={}
 with REGISTRY.open(encoding="utf-8-sig",newline="") as f:
  for x in csv.DictReader(f):
   ticker=x.get("ticker","")
   if ticker not in allowed or x.get("status")!="OK":continue
   cik=x.get("cik10","")
   if not CIK.fullmatch(cik) or cik=="0000000000" or ticker in out:
    raise ValueError("CONFLICTING_OR_INVALID_CIK:"+ticker)
   out[ticker]={"ticker":ticker,"cik":cik,"directoryCompany":x.get("company","")}
 return [(ticker,out.get(ticker)) for ticker in sorted(allowed)]
def browse_filing(cik,accession):
 if not re.fullmatch(r"\d{10}-\d{2}-\d{6}",str(accession)):
  return None
 return "https://www.sec.gov/Archives/edgar/data/"+str(int(cik))+"/"+accession.replace("-","")+"/"
def parse_companyfacts(data,cik,as_of):
 if str(data.get("cik","")).zfill(10)!=cik:
  raise ValueError("SEC_COMPANYFACTS_CIK_MISMATCH")
 facts=data.get("facts",{})
 found=[]
 for label,keys in METRICS.items():
  best=[]
  for tax,tag in keys:
   concept=facts.get(tax,{}).get(tag,{})
   for unit,observations in concept.get("units",{}).items():
    if unit not in ("USD","EUR","shares"):continue
    for record in observations:
     date_end=record.get("end");filed=record.get("filed");value=record.get("val")
     if not isinstance(filed,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",filed) or \
        not isinstance(date_end,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",date_end) or \
        not date_end<=filed<=as_of or record.get("form") not in ALLOWED_FORMS or \
        isinstance(value,bool) or not isinstance(value,(int,float)):
      continue
     # Companyfacts often includes stale amended/overlapping forms. Select
     # most recently filed observation of a specific preferred concept.
     # Never sum or currency-convert mixed classes, units or financial periods.
     if date.fromisoformat(as_of).toordinal()-date.fromisoformat(date_end).toordinal()>900:continue
     best.append({"metric":label,"value":value,"unit":unit,
       "periodEnd":date_end,"periodStart":record.get("start"),
       "filed":filed,"form":record["form"],"accession":record.get("accn"),
       "taxonomy":tax,"tag":tag,
       "filingUrl":browse_filing(cik,record.get("accn")),
       "sourceUrl":"https://data.sec.gov/api/xbrl/companyfacts/CIK"+cik+".json",
       "status":"SEC_REPORTED_ISSUER_FACT_NEEDS_PROGRAM_RECONCILIATION"})
  # Prefer listed keys in priority order only if same currency and period.
  # Keep ambiguities as a queue rather than pick financial facts arbitrarily.
  if best:
   priority={v:i for i,v in enumerate(keys)}
   best.sort(key=lambda x:(x["filed"],x["periodEnd"],
      -priority[(x["taxonomy"],x["tag"])]),reverse=True)
   first=best[0]
   peers=[x for x in best if x["filed"]==first["filed"] and
      x["periodEnd"]==first["periodEnd"] and x["unit"]==first["unit"] and
      x["taxonomy"]==first["taxonomy"] and x["tag"]==first["tag"]]
   if len({x["value"] for x in peers})>1:
    found.append({"metric":label,"status":"CONFLICTING_SEC_VALUES_NEED_REVIEW",
      "sourceUrl":first["sourceUrl"],"candidates":len(peers)})
   else:
    found.append(first)
 return found
def parse_submissions(data,cik,ticker,as_of):
 if str(data.get("cik","")).zfill(10)!=cik:
  raise ValueError("SEC_SUBMISSIONS_CIK_MISMATCH")
 tickers=data.get("tickers",[])
 if ticker not in tickers:
  raise ValueError("SEC_ISSUER_TICKER_NOT_IN_SUBMISSIONS:"+ticker)
 recent=data.get("filings",{}).get("recent",{})
 keys=("accessionNumber","form","filingDate","primaryDocument")
 if not all(isinstance(recent.get(k),list) for k in keys):
  raise ValueError("SEC_SUBMISSIONS_SCHEMA_INVALID")
 count=min(len(recent[k]) for k in keys)
 leads=[]
 for i in range(count):
  acc,form,filing,doc=(recent[k][i] for k in keys)
  if form not in ("10-K","10-Q","20-F","40-F","8-K","6-K") or \
     not re.fullmatch(r"\d{4}-\d{2}-\d{2}",str(filing)) or \
     not str(filing)<=as_of:continue
  url=browse_filing(cik,acc)
  if not url or not re.fullmatch(r"[a-zA-Z0-9_.-]{1,160}",str(doc)):continue
  leads.append({"form":form,"filed":filing,"url":url+doc,
    "status":"SEC_FILING_LEAD_NOT_REVIEWED_FOR_PRODUCT_RIGHTS"})
  if len(leads)>=8:break
 return leads

def collect_one(pair,as_of):
 ticker,record=pair
 if not record:
  return {"ticker":ticker,"status":"SEC_CIK_UNMAPPED","facts":[],
          "filingLeads":[],"issuerRightsVerified":False}
 cik=record["cik"]
 result={"ticker":ticker,"cik":cik,"directoryCompany":record["directoryCompany"],
   "sourceAsOf":as_of,"facts":[],"filingLeads":[],
   "issuerRightsVerified":False,"status":"SEC_SOURCE_LOOKUP_REQUIRED"}
 try:
  submissions=sec_get("https://data.sec.gov/submissions/CIK"+cik+".json",max_bytes=5_000_000)
  result["filingLeads"]=parse_submissions(submissions,cik,ticker,as_of)
  result["secCompanyName"]=submissions.get("name")
  result["status"]="SEC_ISSUER_IDENTITY_CONFIRMED_RIGHTS_NOT_ESTABLISHED"
  try:
   facts=sec_get("https://data.sec.gov/api/xbrl/companyfacts/CIK"+cik+".json",max_bytes=11_000_000)
   result["facts"]=parse_companyfacts(facts,cik,as_of)
  except Exception as e:
   result["factsError"]=type(e).__name__+":"+str(e)[:120]
 except Exception as e:
  result["status"]="SEC_SOURCE_UNAVAILABLE"
  result["sourceError"]=type(e).__name__+":"+str(e)[:120]
 return result
def run():
 as_of=today()
 issuers=index()
 collected=[]
 with ThreadPoolExecutor(max_workers=2) as pool:
  futures={pool.submit(collect_one,item,as_of):item for item in issuers}
  for future in as_completed(futures):
   collected.append(future.result())
 collected.sort(key=lambda x:x["ticker"])
 report={"schemaVersion":1,"asOf":as_of,"issuerCount":len(issuers),
   "issuerIdentityConfirmed":sum(x["status"]=="SEC_ISSUER_IDENTITY_CONFIRMED_RIGHTS_NOT_ESTABLISHED" for x in collected),
   "sourceUnavailable":sum(x["status"]=="SEC_SOURCE_UNAVAILABLE" for x in collected),
   "financialFactRows":sum(len(x["facts"]) for x in collected),
   "filingDocumentLeads":sum(len(x["filingLeads"]) for x in collected),
   "productRightsVerified":0,"statusCounts":dict(Counter(x["status"] for x in collected)),
   "note":"Issuer financials do not establish trial drug rights, commercial value, royalties or a forecast."}
 atomic(RESULT,{"schemaVersion":1,"issuers":collected})
 atomic(SUMMARY,report)
 print(json.dumps(report,sort_keys=True))
 return report
if __name__=="__main__":
 run()
