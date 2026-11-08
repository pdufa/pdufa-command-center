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
from urllib.parse import urlparse, urlencode
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
DOSSIER=ROOT/"new-platform/frontend/data/raas-v2-nov14-issuer-goal-continuity.json"
SCOPE="RAAS_V2_SEC_NOV14_ISSUER_RECENT_FILINGS_LEADS_NOT_FDA_DECISIONS"
CASES={
  "CYTK":("0001061983","2026-08-06","CYTK|MYQORZO_HCM_20261114"),
  "SMMT":("0001599298","2026-10-21","SMMT|IVONESCIMAB_20261114"),
}
REVIEW_FORMS={"8-K","8-K/A","10-Q","10-Q/A","10-K","10-K/A"}
MAX_SOURCE_BYTES=3_000_000
MAX_CANDIDATES=25
ATOM_NS="{http://www.w3.org/2005/Atom}"
ATOM_MAX_ENTRIES=250
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



def official_atom_url(ticker):
    """A documented SEC company-filings RSS/Atom query, not a bypass endpoint."""
    require(ticker in CASES,"ATOM_TICKER_NOT_AUTHORIZED")
    cik=CASES[ticker][0]
    return ("https://www.sec.gov/cgi-bin/browse-edgar?"+
            urlencode({"action":"getcompany","CIK":cik,
                       "type":"","count":"100","output":"atom"}))


def inspect_atom_company(ticker,body,status,detail,clock):
    """Validate actual SEC filing links/CIK before listing candidates."""
    require(ticker in CASES,"ATOM_UNKNOWN_COMPANY")
    require(status in {"NOT_QUERIED","AVAILABLE","SOURCE_UNAVAILABLE",
                "HTTP_404_NO_PUBLIC_RECORD","MALFORMED_RESPONSE"},
            "ATOM_SOURCE_STATUS_INVALID")
    require(status=="AVAILABLE" or body is None,
            "ATOM_MISMATCHED_BODY_AND_STATUS")
    cik,cutoff,key=CASES[ticker]
    candidates=[]
    entries_seen=0
    if status=="AVAILABLE":
        require(isinstance(body,str) and 0<len(body)<=MAX_SOURCE_BYTES,
                "ATOM_INVALID_BODY_SIZE")
        try:
            root=ET.fromstring(body)
        except ET.ParseError as exc:
            raise ValueError("RAAS_SEC_ISSUER_WATCH_ATOM_XML_INVALID") from exc
        require(root.tag==ATOM_NS+"feed","ATOM_NOT_ATOM_FEED")
        entries=root.findall(ATOM_NS+"entry")
        require(len(entries)<=ATOM_MAX_ENTRIES,"ATOM_TOO_MANY_ENTRIES")
        entries_seen=len(entries)
        seen=set()
        for entry in entries:
            category=entry.find(ATOM_NS+"category")
            form=(category.get("term") if category is not None else None)
            if form not in REVIEW_FORMS:
                # Older EDGAR Atom variants put the form in the title.
                title=entry.findtext(ATOM_NS+"title") or ""
                match=re.match(r"^(8-K/A|8-K|10-Q/A|10-Q|10-K/A|10-K)(?:\s|\s*[-:])",title)
                form=match.group(1) if match else None
            if form not in REVIEW_FORMS:
                continue
            stamp=entry.findtext(ATOM_NS+"updated")
            require(isinstance(stamp,str) and
                    re.match(r"^\d{4}-\d{2}-\d{2}T",stamp),
                    "ATOM_FILING_TIMESTAMP_INVALID")
            try:
                filed=dt.date.fromisoformat(stamp[:10])
            except ValueError as exc:
                raise ValueError("RAAS_SEC_ISSUER_WATCH_ATOM_FILED_DATE_INVALID") from exc
            if filed<=as_day(cutoff) or filed>clock.date():
                continue
            links=[el.get("href") for el in entry.findall(ATOM_NS+"link")]
            valid=[]
            for link in links:
                if not isinstance(link,str):
                    continue
                parsed=urlparse(link)
                if parsed.scheme!="https" or parsed.netloc!="www.sec.gov" or (
                        parsed.query or parsed.fragment or parsed.username or parsed.password):
                    continue
                # An Atom index link must be to the exact issuer CIK, never
                # another issuer with the same agent-accession prefix.
                if not re.fullmatch(
                    r"/Archives/edgar/data/"+str(int(cik))+
                    r"/\d{18}/[A-Za-z0-9_.-]{1,160}",parsed.path):
                    continue
                valid.append(link)
            require(len(valid)>0,"ATOM_FILING_LINK_CIK_IDENTITY_NOT_CONFIRMED")
            link=valid[0]
            if link in seen:
                continue
            seen.add(link)
            candidates.append({
                "form":form,"filedDate":filed.isoformat(),
                "officialSecFilingLink":link,
                "documentReviewedForPdufaGoal":False,
                "fdaDeadlineRevisionConfirmed":False,
                "pendingFdaApplicationNumberConfirmed":False,
                "fdaActionOrPredictionConfirmed":False,
            })
    candidates.sort(key=lambda x:(x["filedDate"],x["officialSecFilingLink"]),
                    reverse=True)
    return {
        "officialSecCompanyAtomFeedUrl":official_atom_url(ticker),
        "sourceStatus":status,
        "sourceDetail":(detail or "")[:200],
        "feedEntryCount":entries_seen,
        "newerRelevantFormFilingCount":len(candidates),
        "newerFilingReviewCandidates":candidates[:MAX_CANDIDATES],
        "additionalMatchingFilingsOmittedByDisplayCap":max(
            0,len(candidates)-MAX_CANDIDATES),
        "atomFeedAloneVerifiesCompleteIssuerSECFileHistory":False,
        "absenceFromAtomFeedProvesNoFdaDeadlineChange":False,
        "aFilingLinkIdentifiesCurrentPendingBlaOrSNda":False,
        "atomFeedAccessNotTheSameAsRestApiAccess":True,
    }


def inspect_watch(payloads,statuses,details,checked_at,dossier=None,
                  atom_payloads=None,atom_statuses=None,atom_details=None):
    clock=parse_clock(checked_at)
    base=dossier or json.loads(DOSSIER.read_text("utf-8"))
    validate_dossier(base)
    require(isinstance(payloads,dict) and isinstance(statuses,dict)
        and isinstance(details,dict) and
        set(payloads)==set(statuses)==set(details)==set(CASES),
        "MISSING_COMPANY_SOURCE_STATUS")
    rows=[inspect_company(t,payloads[t],statuses[t],details[t],clock,base)
          for t in ("CYTK","SMMT")]
    if atom_payloads is None and atom_statuses is None and atom_details is None:
        atom_payloads={"CYTK":None,"SMMT":None}
        atom_statuses={"CYTK":"NOT_QUERIED","SMMT":"NOT_QUERIED"}
        atom_details={"CYTK":None,"SMMT":None}
    require(all(isinstance(v,dict) and set(v)==set(CASES)
                for v in (atom_payloads,atom_statuses,atom_details)),
            "ATOM_MISSING_COMPANY_SOURCE_STATUS")
    for row in rows:
        t=row["ticker"]
        row["alternativeOfficialSecAtomFeed"]=inspect_atom_company(
            t,atom_payloads[t],atom_statuses[t],atom_details[t],clock)
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
        "alternativeOfficialSecAtomAvailableCount":sum(
            r["alternativeOfficialSecAtomFeed"]["sourceStatus"]=="AVAILABLE"
            for r in rows),
        "effectiveOfficialSecFilingSourceCoverageCount":sum(
            r["sourceStatus"]=="AVAILABLE" or
            r["alternativeOfficialSecAtomFeed"]["sourceStatus"]=="AVAILABLE"
            for r in rows),
        "officialSecAtomResearchFilingCandidateCount":sum(
            r["alternativeOfficialSecAtomFeed"]["newerRelevantFormFilingCount"]
            for r in rows),
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


def fetch_atom_company(ticker):
    require(ticker in CASES,"ATOM_FETCH_UNKNOWN_COMPANY")
    agent=(os.environ.get("RAAS_SEC_USER_AGENT") or CONTACT_AGENT).strip()
    require(15<=len(agent)<=350,"ATOM_BAD_SEC_USER_AGENT")
    req=urllib.request.Request(official_atom_url(ticker),headers={
        "User-Agent":agent,"Accept":"application/atom+xml,application/xml"})
    try:
        with urllib.request.urlopen(req,timeout=15) as response:
            raw=response.read(MAX_SOURCE_BYTES+1)
        require(len(raw)<=MAX_SOURCE_BYTES,"ATOM_BODY_TOO_LARGE")
        try:
            return raw.decode("utf-8"),"AVAILABLE",None
        except UnicodeError:
            return None,"MALFORMED_RESPONSE","SEC Atom body not UTF-8"
    except urllib.error.HTTPError as exc:
        if exc.code==404:
            return None,"HTTP_404_NO_PUBLIC_RECORD","SEC Atom HTTP 404"
        return None,"SOURCE_UNAVAILABLE","SEC Atom HTTP "+str(exc.code)
    except (OSError,TimeoutError) as exc:
        return None,"SOURCE_UNAVAILABLE",type(exc).__name__


def main():
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    inputs={t:fetch_company(t) for t in ("CYTK","SMMT")}
    # Official SEC Atom feeds are consulted only if direct JSON was blocked.
    atom={}
    for t in ("CYTK","SMMT"):
        atom[t]=(None,"NOT_QUERIED",None) if inputs[t][1]=="AVAILABLE" else (
            fetch_atom_company(t))
    try:
        report=inspect_watch(
            {t:inputs[t][0] for t in inputs},
            {t:inputs[t][1] for t in inputs},
            {t:inputs[t][2] for t in inputs},stamp,
            atom_payloads={t:atom[t][0] for t in atom},
            atom_statuses={t:atom[t][1] for t in atom},
            atom_details={t:atom[t][2] for t in atom})
    except ValueError:
        # Malformed feed contents fail closed; a status-only rerun retains
        # primary JSON results without treating Atom as trustworthy evidence.
        report=inspect_watch(
            {t:inputs[t][0] for t in inputs},
            {t:inputs[t][1] for t in inputs},
            {t:inputs[t][2] for t in inputs},stamp,
            atom_payloads={"CYTK":None,"SMMT":None},
            atom_statuses={"CYTK":"MALFORMED_RESPONSE",
                           "SMMT":"MALFORMED_RESPONSE"},
            atom_details={"CYTK":"SEC feed parse/identity validation failed",
                          "SMMT":"SEC feed parse/identity validation failed"})
    out=Path(os.getenv("RAAS_SEC_NOV14_REVIEW_JSON",
            "raas-v2-sec-nov14-new-filing-review-leads.json"))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",
                   encoding="utf-8")
    print(json.dumps({k:report[k] for k in (
        "checkedAtUTC","sourceAvailableCount","sourceCoverageStatus",
        "alternativeOfficialSecAtomAvailableCount",
        "effectiveOfficialSecFilingSourceCoverageCount",
        "officialSecAtomResearchFilingCandidateCount",
        "issuerFamiliesWithNewerFilings",
        "potentialNewFilingReviewCandidates",
        "newThreeWayForecastsFromFilings")},sort_keys=True))


if __name__=="__main__":
    main()
