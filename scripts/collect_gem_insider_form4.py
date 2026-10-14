#!/usr/bin/env python3
"""Capped issuer SEC Form 4 collector for PDUFA GEM research watchlist.

Uses SEC issuer CIK (not ticker-only) to identify filed ownership documents.
Only dated, priced nonderivative common-share codes P/A or S/D are classified.
Source access failure is explicit; partial issuer scans never get buy totals.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from sec_step4 import load_registry  # noqa: E402
from scripts.collect_gem_runway import read_candidates, eligible_tickers  # noqa: E402
from scripts.collect_gem_hedge_funds import sec_get  # noqa: E402
from gem_insider import FILE, LOOKBACK_DAYS, _day, _int, _cash  # noqa: E402

SEC="https://data.sec.gov"
ARCHIVE="https://www.sec.gov/Archives/edgar/data"


def leaf(node):
    return str(node.tag).rsplit("}",1)[-1]


def child(node,name):
    if node is None:
        return None
    for x in node:
        if leaf(x)==name:
            return x
    return None


def value(node,path):
    current=node
    for key in path.split("/"):
        current=child(current,key)
        if current is None:
            return ""
    return "".join(current.itertext()).strip()


def parse_form4(raw, *, ticker, issuer_cik, filed, as_of, source):
    """Reject unmatched issuer CIK and non-market/grant/option securities."""
    try:
        root=ET.fromstring(raw)
    except (ET.ParseError, TypeError) as exc:
        raise ValueError("Malformed SEC Form 4 XML") from exc
    if leaf(root)!="ownershipDocument" or value(root,"documentType") != "4":
        raise ValueError("Not a regular SEC Form 4 ownership document")
    declared=value(root,"issuer/issuerCik")
    if not declared.isdigit() or int(declared)!=int(issuer_cik):
        raise ValueError("SEC Form 4 issuer CIK mismatch")
    owners=[
        value(o,"reportingOwnerId/rptOwnerName") for o in root
        if leaf(o)=="reportingOwner"
    ]
    if not owners or any(not o for o in owners):
        raise ValueError("SEC Form 4 reporting owner identity missing")
    filing_date=_day(filed)
    if filing_date is None or filing_date>as_of:
        raise ValueError("SEC Form 4 filing date is future/invalid")
    output=[]
    for tab in root:
        if leaf(tab)!="nonDerivativeTable":
            continue
        for node in tab:
            if leaf(node)!="nonDerivativeTransaction":
                continue
            title=value(node,"securityTitle/value").upper()
            if not ("COMMON" in title or "ORDINARY" in title or
                    re.fullmatch(r"COM(?:MON)?(?: STK| STOCK)?",title)):
                continue
            code=value(node,"transactionCoding/transactionCode").upper()
            direction=value(node,"transactionAmounts/transactionAcquiredDisposedCode/value").upper()
            if (code,direction) not in (("P","A"),("S","D")):
                continue
            when=_day(value(node,"transactionDate/value"))
            shares=_int(value(node,"transactionAmounts/transactionShares/value"))
            price=_cash(value(node,"transactionAmounts/transactionPricePerShare/value"))
            if (not when or not 0 <= (as_of-when).days <= LOOKBACK_DAYS
                    or when>filing_date or not shares or price is None):
                continue
            output.append({
                "ticker": ticker, "owner": "; ".join(owners),
                "code": code, "date": when.isoformat(),
                "shares": shares, "price": round(price,5),
                "source": source, "filed": filing_date.isoformat(),
            })
    return output


def filings_for_issuer(submissions, cik, *, as_of, max_filings=25):
    if (not isinstance(submissions,dict)
            or not str(submissions.get("cik") or "").isdigit()
            or int(submissions["cik"])!=int(cik)):
        raise ValueError("Issuer filings source CIK not verified")
    recent=submissions.get("filings",{}).get("recent",{})
    fields=("form","filingDate","accessionNumber","primaryDocument")
    if not isinstance(recent,dict) or any(not isinstance(recent.get(k),list) for k in fields):
        raise ValueError("Missing SEC issuer filing index")
    if len(set(len(recent[k]) for k in fields))!=1:
        raise ValueError("SEC issuer filing arrays truncated")
    ordinary=[]
    amended=set()
    for form,day_text,acc,doc in zip(*(recent[k] for k in fields)):
        filing=_day(day_text)
        if (not filing or filing>as_of or (as_of-filing).days>LOOKBACK_DAYS+15
                or not re.fullmatch(r"\d{10}-\d{2}-\d{6}",str(acc))):
            continue
        if form=="4/A":
            amended.add(str(acc))
        if form=="4":
            ordinary.append({"accession":str(acc),"filed":filing.isoformat(),
                             "primary":str(doc or "")})
    if amended:
        # Without a reliable link between amendments and originals, abstain
        # from asserting issuer-wide complete 90-day transaction coverage.
        raise ValueError("SEC issuer Form 4 amendments require manual reconciliation")
    if len(ordinary)>max_filings:
        raise ValueError("More than capped Form 4 filings — not a complete lookback")
    return ordinary


def xml_for_filing(cik, filing, agent, *, fetch=sec_get):
    folder=f"{ARCHIVE}/{int(cik)}/{filing['accession'].replace('-','')}"
    primary=filing["primary"]
    # The SEC primaryDocument may be an HTML rendering; source-linked XML is
    # selected from archive index to avoid mistaking presentation for raw data.
    if (re.fullmatch(r"[A-Za-z0-9_.\-]{1,100}",primary)
            and primary.lower().endswith(".xml")):
        name=primary
    else:
        time.sleep(0.15)
        listing=json.loads(fetch(folder+"/index.json",agent))
        choices=[
            x["name"] for x in listing.get("directory",{}).get("item",[])
            if isinstance(x,dict) and re.fullmatch(
                r"[A-Za-z0-9_.\-]{1,100}",str(x.get("name") or "")
            ) and str(x.get("name")).lower().endswith(".xml")
            and ("form4" in str(x["name"]).lower() or
                 "ownership" in str(x["name"]).lower())
        ]
        if len(choices)!=1:
            # Some EDGAR filing folders call the raw ownership document
            # primary_doc.xml or form.xml. A *single* XML can be parsed
            # and is still validated by root type and exact issuer CIK.
            all_xml=[
                str(x.get("name") or "") for x in listing.get("directory",{}).get("item",[])
                if isinstance(x,dict) and re.fullmatch(
                    r"[A-Za-z0-9_.\-]{1,100}",str(x.get("name") or "")
                ) and str(x.get("name") or "").lower().endswith(".xml")
            ]
            if len(all_xml)==1:
                choices=all_xml
            else:
                raise ValueError("SEC Form 4 XML document missing or ambiguous")
        name=choices[0]
    time.sleep(0.15)
    uri=folder+"/"+name
    return fetch(uri,agent),uri


def collect(root, *, as_of, agent, fetch=sec_get, max_tickers=75):
    root=Path(root)
    registry=load_registry(root/"company_registry.csv")
    tickers=eligible_tickers(read_candidates(root/"pdufa_candidates.csv"),
                             registry, as_of=as_of, limit=max_tickers)
    records=[]
    errors=[]
    for ticker in tickers:
        cik=registry[ticker]["cik"]
        item={"ticker":ticker,"cik":cik,"as_of":as_of.isoformat(),
              "status":"INCOMPLETE", "filings_reviewed":0,
              "transactions":[], "latest_filing":""}
        try:
            if not isinstance(agent,str) or "@" not in agent or len(agent.strip())<12:
                raise ValueError("SEC_USER_AGENT required")
            time.sleep(0.15)
            payload=json.loads(fetch(f"{SEC}/submissions/CIK{cik}.json",agent))
            filings=filings_for_issuer(payload,cik,as_of=as_of)
            trans=[]
            for f in filings:
                raw,url=xml_for_filing(cik,f,agent,fetch=fetch)
                trans.extend(parse_form4(raw,ticker=ticker,issuer_cik=cik,
                                         filed=f["filed"],as_of=as_of,source=url))
            item.update({
                "status":"COMPLETE","transactions":trans,
                "filings_reviewed":len(filings),
                "latest_filing":max((f["filed"] for f in filings),default=""),
            })
        except (OSError,TypeError,ValueError,RuntimeError,KeyError,ET.ParseError) as exc:
            item["error"]=str(exc)[:200]
            errors.append({"ticker":ticker,"error":str(exc)[:200]})
        records.append(item)
    complete=sum(x["status"]=="COMPLETE" for x in records)
    report={
        "schema_version":1, "source":"SEC_ISSUER_FORM4_XML",
        "as_of_pacific":as_of.isoformat(),
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "collector_status":(
            "COMPLETE — TARGETED ISSUERS" if tickers and complete==len(tickers)
            else "PARTIAL — ISSUER SOURCE FAILURES" if complete
            else "NO VERIFIED ISSUER COVERAGE"
        ),
        "issuer_count":len(tickers),"issuers_complete":complete,
        "issuer_errors":errors, "records":records,
        "limits":("Issuer filing index capped to 25 Form 4 documents per 105-day "
                  "window, 90-day transaction window. Source errors and "
                  "amendments require manual review. P/S does not guarantee "
                  "discretionary investment or future returns."),
    }
    root.mkdir(parents=True,exist_ok=True)
    path=root/FILE
    tmp=path.with_name(path.name+".tmp")
    tmp.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    tmp.replace(path)
    return report


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir",type=Path,default=ROOT/"data")
    p.add_argument("--as-of",type=str)
    p.add_argument("--max-tickers",type=int,default=75)
    a=p.parse_args(argv)
    if a.max_tickers<1 or a.max_tickers>75:
        p.error("--max-tickers must be 1..75")
    asof=date.fromisoformat(a.as_of) if a.as_of else datetime.now(
        ZoneInfo("America/Los_Angeles")).date()
    report=collect(a.data_dir,as_of=asof,agent=os.getenv("SEC_USER_AGENT",""),
                   max_tickers=a.max_tickers)
    print(json.dumps({k:report[k] for k in (
        "collector_status","issuer_count","issuers_complete"
    )},sort_keys=True))
    # Incomplete coverage is explicitly reported; do not block core GEM run.
    return 0


if __name__=="__main__":
    raise SystemExit(main())
