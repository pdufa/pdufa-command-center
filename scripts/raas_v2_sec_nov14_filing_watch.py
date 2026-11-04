#!/usr/bin/env python3
"""Read-only SEC EDGAR new-filing lead watch for the two November 14 cases.

A newer filing is a DOCUMENT FOR REVIEW, never evidence by itself of a PDUFA
date change, an FDA application number, PASS/CRL/EXTENSION, or a prediction.
This monitor never downloads or interprets filing contents.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
DOSSIER=ROOT/"new-platform/frontend/data/raas-v2-nov14-issuer-goal-continuity.json"
SCOPE="RAAS_V2_SEC_NOV14_ISSUER_RECENT_FILINGS_LEADS_NOT_FDA_DECISIONS"
CASES={
  "CYTK":("0001061983","2026-08-06","CYTK|MYQORZO_HCM_20261114"),
  "SMMT":("0001599298","2026-09-15","SMMT|IVONESCIMAB_20261114"),
}
REVIEW_FORMS={"8-K","8-K/A","10-Q","10-Q/A","10-K","10-K/A"}
MAX_SOURCE_BYTES=3_000_000
MAX_CANDIDATES=25
CONTACT_AGENT="PDUFACommandCenterResearch/1.0 (+https://github.com/pdufa/pdufa-command-center/issues)"


def require(ok,code):
    if not ok: raise ValueError("RAAS_SEC_ISSUER_WATCH_"+code)


def parse_clock(utc):
    require(isinstance(utc,str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z",utc),"UTC_CLOCK_INVALID")
    return dt.datetime.strptime(utc,"%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=dt.timezone.utc)


def as_day(day):
    require(isinstance(day,str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}",day),
            "FILING_DATE_FORMAT")
    return dt.date.fromisoformat(day)


def validate_dossier(d):
    require(isinstance(d,dict) and d.get("scope")==
        "RAAS_V2_NOV14_DATED_ISSUER_GOAL_CONTINUITY_NOT_INDEPENDENT_FDA_CYCLE_VERIFICATION"
        and d.get("latestDatedIssuerGoalContinuityCases")==2
        and d.get("independentlyVerifiedCurrentFdaReviewCycleCount")==0
        and d.get("independentlyVerifiedNoSubsequentGoalRevisionsCount")==0
        and d.get("prospectivelyFrozenThreeWayForecastCount")==0,
        "INVALID_GOAL_CONTINUITY_BASELINE")
    cases={r.get("ticker"):r for r in d.get("records",[])}
    require(set(cases)==set(CASES) and len(d["records"])==2,
            "WRONG_FDA_CASE_COVERAGE")
    for ticker,(cik,date,key) in CASES.items():
        r=cases[ticker]
        require(r.get("researchCaseKey")==key
            and r.get("issuerPublicSourceDate")==date
            and r.get("reportedGoalDate")=="2026-11-14"
            and r.get("originalNov14GoalStillListedByIssuerAtSourceDate") is True
            and r.get("absenceOfLaterGoalChangeIndependentlyEstablished") is False
            and r.get("fullDatedFDAActionCycleIndependentlyEstablished") is False,
            "INVALID_LAST_SOURCE_OR_FDA_CERTIFICATION")
    return cases


def filing_url(cik,accession,document):
    require(re.fullmatch(r"\d{10}-\d{2}-\d{6}",accession) is not None
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,150}",document) is not None
        and ".." not in document,
        "UNSAFE_EDGAR_FILING_PATH")
    # The accession prefix may identify the filing agent, not the issuer CIK.
    return ("https://www.sec.gov/Archives/edgar/data/"+
            str(int(cik))+"/"+accession.replace("-","")+"/"+document)


def inspect_company(ticker,payload,source_status,detail,clock,dossier):
    require(ticker in CASES,"UNKNOWN_CIK")
    cik,cutoff,key=CASES[ticker]
    require(source_status in {"AVAILABLE","HTTP_404_NO_PUBLIC_RECORD",
        "SOURCE_UNAVAILABLE","MALFORMED_RESPONSE"},"INVALID_SOURCE_STATUS")
    require(source_status=="AVAILABLE" or payload is None,
            "SOURCE_STATUS_PAYLOAD_MISMATCH")
    candidates=[]
    total_rows=0
    latest_filed=None
    if source_status=="AVAILABLE":
        require(isinstance(payload,dict) and payload.get("cik")==int(cik)
            and isinstance(payload.get("tickers"),list)
            and ticker in payload["tickers"],"SEC_CIK_TICKER_IDENTITY_MISMATCH")
        recent=payload.get("filings",{}).get("recent")
        require(isinstance(recent,dict),"RECENT_FILINGS_MISSING")
        keys=("form","filingDate","accessionNumber","primaryDocument")
        require(all(isinstance(recent.get(k),list) for k in keys),
                "RECENT_FILINGS_COLUMNS_INVALID")
        size=len(recent["form"])
        require(size<8000 and all(len(recent[k])==size for k in keys),
                "RECENT_FILINGS_COLUMNS_MISALIGNED")
        total_rows=size
        seen=set()
        cutoff_day=as_day(cutoff)
        for i in range(size):
            form=recent["form"][i]
            if form not in REVIEW_FORMS:continue
            filed=as_day(recent["filingDate"][i])
            if filed<=cutoff_day or filed>clock.date():continue
            accession=recent["accessionNumber"][i]
            document=recent["primaryDocument"][i]
            require(accession not in seen,"DUPLICATE_FILING_ACCESSION")
            seen.add(accession)
            url=filing_url(cik,accession,document)
            candidates.append({
                "form":form,"filedDate":filed.isoformat(),
                "accessionNumber":accession,"documentUrl":url,
                "newerThanLastSelectedIssuerGoalSource":True,
                "documentReviewedForPdufaGoal":False,
                "fdaDeadlineRevisionConfirmed":False,
                "pendingFdaApplicationNumberConfirmed":False,
                "fdaActionOrPredictionConfirmed":False,
            })
        candidates.sort(key=lambda x:(x["filedDate"],x["accessionNumber"]),
                        reverse=True)
        latest_filed=candidates[0]["filedDate"] if candidates else None
    return {
        "ticker":ticker,"researchCaseKey":key,"secCIK":cik,
        "officialSubmissionsUrl":
            "https://data.sec.gov/submissions/CIK"+cik+".json",
        "lastSelectedGoalSourceDate":cutoff,
        "sourceStatus":source_status,
        "sourceDetail":(detail or "")[:200],
        "fdaGoalAsOfLastIssuerSource":"2026-11-14",
        "sourceRowsRead":total_rows,
        "newerRelevantFormFilingCount":len(candidates),
        "latestNewerFilingDate":latest_filed,
        "newerFilingReviewCandidates":candidates[:MAX_CANDIDATES],
        "additionalMatchingFilingsOmittedByDisplayCap":
            max(0,len(candidates)-MAX_CANDIDATES),
        "newFilingAutomaticallyMeansPdufaChange":False,
        "absenceOfNewFilingProvesNoFDAExtension":False,
        "independentlyVerifiedCurrentFDAApplicationCycle":False,
        "certifiedFDADeadlineRevision":False,
        "newThreeWayPredictionFrozen":False,
    }


def inspect_watch(payloads,statuses,details,checked_at,dossier=None):
    clock=parse_clock(checked_at)
    base=dossier or json.loads(DOSSIER.read_text("utf-8"))
    validate_dossier(base)
    require(isinstance(payloads,dict) and isinstance(statuses,dict)
        and isinstance(details,dict) and
        set(payloads)==set(statuses)==set(details)==set(CASES),
        "MISSING_COMPANY_SOURCE_STATUS")
    rows=[inspect_company(t,payloads[t],statuses[t],details[t],clock,base)
          for t in ("CYTK","SMMT")]
    return {
        "schemaVersion":1,"scope":SCOPE,
        "status":"ISSUER_FILING_LEADS_ONLY_NO_PDUFA_EXTENSION_VERIFICATION",
        "checkedAtUTC":checked_at,
        "monitoredIssuerFamilies":2,
        "sourceAvailableCount":sum(r["sourceStatus"]=="AVAILABLE" for r in rows),
        "sourceCoverageStatus":(
            "TWO_ISSUER_SOURCES_AVAILABLE"
            if all(r["sourceStatus"]=="AVAILABLE" for r in rows)
            else "PARTIAL_ISSUER_SOURCE_ACCESS"
            if any(r["sourceStatus"]=="AVAILABLE" for r in rows)
            else "ISSUER_SOURCES_UNAVAILABLE_NOT_ZERO_NEW_FILINGS"),
        "issuerFamiliesWithNewerFilings":sum(
            r["newerRelevantFormFilingCount"]>0 for r in rows),
        "potentialNewFilingReviewCandidates":sum(
            r["newerRelevantFormFilingCount"] for r in rows),
        "rows":rows,
        "independentlyVerifiedNoFurtherFDAExtensions":0,
        "independentlyVerifiedCurrentFDAApplicationCycles":0,
        "newThreeWayForecastsFromFilings":0,
        "approvedRAASMetricCalibrations":0,
        "warning":"Only SEC 8-K/10-Q/10-K and amendments newer than the last "
        "selected dated issuer goal confirmation are source-review leads. "
        "No filing, lack of a filing, or retrieval failure by itself proves "
        "an FDA extension, application number, approval, CRL or unchanged "
        "PDUFA goal. Review actual documents and FDA evidence separately.",
    }


def fetch_company(ticker):
    require(ticker in CASES,"UNKNOWN_CIK_FETCH")
    cik=CASES[ticker][0]
    url="https://data.sec.gov/submissions/CIK"+cik+".json"
    agent=(os.environ.get("RAAS_SEC_USER_AGENT") or CONTACT_AGENT).strip()
    require(len(agent)>=15 and len(agent)<=350,"BAD_SEC_USER_AGENT")
    req=urllib.request.Request(url,headers={
        "User-Agent":agent,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=15) as r:
            raw=r.read(MAX_SOURCE_BYTES+1)
        require(len(raw)<=MAX_SOURCE_BYTES,"SEC_RESPONSE_TOO_LARGE")
        try: return json.loads(raw.decode("utf-8")),"AVAILABLE",None
        except (ValueError,UnicodeError):
            return None,"MALFORMED_RESPONSE","SEC source returned invalid JSON"
    except urllib.error.HTTPError as exc:
        if exc.code==404:return None,"HTTP_404_NO_PUBLIC_RECORD","SEC HTTP 404"
        return None,"SOURCE_UNAVAILABLE","SEC HTTP "+str(exc.code)
    except (OSError,TimeoutError) as exc:
        return None,"SOURCE_UNAVAILABLE",type(exc).__name__


def main():
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inputs={t:fetch_company(t) for t in ("CYTK","SMMT")}
    report=inspect_watch(
        {t:inputs[t][0] for t in inputs},
        {t:inputs[t][1] for t in inputs},
        {t:inputs[t][2] for t in inputs},stamp)
    out=Path(os.getenv("RAAS_SEC_NOV14_REVIEW_JSON",
            "raas-v2-sec-nov14-new-filing-review-leads.json"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                   encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "checkedAtUTC","sourceAvailableCount","sourceCoverageStatus",
        "issuerFamiliesWithNewerFilings",
        "potentialNewFilingReviewCandidates",
        "newThreeWayForecastsFromFilings")},sort_keys=True))


if __name__=="__main__":
    main()
