#!/usr/bin/env python3
"""MAIN: alternative original-public-source evidence receipt for ACACIA-HCM.

Read-only, no clinical ledger, no output derived from inaccessible sources.
Cannot authenticate the final locked primary SAP, perform an independent
sensitivity analysis, or reconcile competing HF SAE reports from abstracts.
Stores provenance, not copyrighted full-text/PDF files or patient data.
"""
from __future__ import annotations
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

SCHEMA = "MAIN_ACACIA_ALTERNATIVE_SOURCE_RESEARCH_V1"
NCT = "NCT06081894"
SOURCES = {
    "NEJM_ARTICLE_LANDING": "https://www.nejm.org/doi/10.1056/NEJMoa2603021",
    "EUROPEPMC_RESPONDER_FULLTEXT":
      "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13674601/fullTextXML",
    "EUROPEPMC_ECHO_FULLTEXT":
      "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13674599/fullTextXML",
}
MAX_BYTES = 6_500_000
EXPECTED_NEJM_PROTOCOL = "nejmoa2603021_protocol.pdf"
EXPECTED_NEJM_APPENDIX = "nejmoa2603021_appendix.pdf"
DATA_SHARING_CONTACT = "medicalaffairs@cytokinetics.com"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("REDIRECT_NOT_ALLOWED")

class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.bits=[]
        self.suppressed=0
    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","noscript"}:self.suppressed+=1
    def handle_endtag(self,tag):
        if tag in {"script","style","noscript"}:self.suppressed=max(self.suppressed-1,0)
    def handle_data(self,s):
        if not self.suppressed:self.bits.append(s)

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def normalized(text):
    return re.sub(r"\s+"," ",text).strip()

def fetch_public(source_id):
    if source_id not in SOURCES:
        raise ValueError("NOT_AN_ALLOWLISTED_PUBLIC_SOURCE")
    url=SOURCES[source_id]
    accept="text/html" if source_id=="NEJM_ARTICLE_LANDING" else "application/xml"
    request=Request(url,headers={"Accept":accept,"User-Agent":"MAIN-PDUFA-Public-Research-Audit/1.0"})
    try:
        with build_opener(NoRedirect()).open(request,timeout=16) as response:
            if response.status!=200 or response.geturl()!=url:
                raise ValueError("INVALID_ORIGIN_OR_STATUS")
            content_type=response.headers.get("Content-Type","").lower()
            raw=response.read(MAX_BYTES+1)
    except (HTTPError,URLError,TimeoutError,OSError,ValueError) as err:
        return None,"UNAVAILABLE",type(err).__name__
    if len(raw)>MAX_BYTES:
        return None,"TOO_LARGE","SIZE_CAP"
    if source_id=="NEJM_ARTICLE_LANDING":
        if not ("html" in content_type or raw[:150].lower().find(b"<html")!=-1):
            return None,"WRONG_MEDIA_TYPE","HTML_EXPECTED"
    elif not ("xml" in content_type or raw.lstrip().startswith(b"<?xml") or raw.lstrip().startswith(b"<article")):
        return None,"WRONG_MEDIA_TYPE","XML_EXPECTED"
    return raw,"RETRIEVED",None

def article_landing(raw):
    parser=TextOnly()
    parser.feed(raw.decode("utf-8","replace"))
    text=normalized(" ".join(parser.bits))
    identity=("Aficamten for Symptomatic Nonobstructive Hypertrophic Cardiomyopathy" in text
              and "NEJMoa2603021" in raw.decode("utf-8","replace"))
    if not identity:
        return {"sourceIdentity":"UNVERIFIED","listedProtocol":False,
                "listedAppendix":False,"dataSharingStatementListed":False}
    return {
      "sourceIdentity":"ORIGINAL_PRIMARY_ARTICLE",
      "listedProtocol":EXPECTED_NEJM_PROTOCOL in raw.decode("utf-8","replace"),
      "listedAppendix":EXPECTED_NEJM_APPENDIX in raw.decode("utf-8","replace"),
      "dataSharingStatementListed":"nejmoa2603021_data-sharing.pdf" in raw.decode("utf-8","replace"),
    }

def europe_pmc_xml(raw,kind):
    try:
        node=ET.fromstring(raw)
    except ET.ParseError:
        return {"sourceIdentity":"INVALID_XML"}
    if node.tag.split("}")[-1]!="article":
        return {"sourceIdentity":"WRONG_ROOT"}
    text=normalized(" ".join(node.itertext()))
    title=normalized(" ".join(" ".join(n.itertext()) for n in node.findall(".//article-title")))
    # Exact trial and exact *article* avoid misclassifying adjacent HCM datasets.
    correct=(NCT in text and "aficamten" in title.lower() and
             "nonobstructive" in title.lower() and
             ("global efficacy" in title.lower() if kind=="RESPONDER" else
              "cardiac structure" in title.lower()))
    if not correct:
        return {"sourceIdentity":"UNVERIFIED"}
    if kind=="RESPONDER":
        return {
          "sourceIdentity":"EXACT_TRIAL_SECONDARY_RESPONDER_ARTICLE",
          "responderAnalysisDescribedAsPrespecified":
            bool(re.search(r"(secondary analysis.{0,100}statistical analysis plan|"
                           r"statistical analysis plan.{0,120}before database lock)",text,re.I)),
          "lastAvailableObservationDescribed":
            bool(re.search(r"last available observation.{0,110}week 8.{0,80}week 36",text,re.I)),
          "zeroPostWeek8ClassifiedNonresponder":
            bool(re.search(r"no available data on or after week 8.{0,100}nonresponder",text,re.I)),
          "sponsorDataRequestContactListed":DATA_SHARING_CONTACT in text.lower(),
          "hfEvent11vs1Mentioned":
            bool(re.search(r"heart failure.{0,190}\b11\b.{0,100}\b1\b",text,re.I)),
          "isFinalLockedPrimarySap":False,
          "isPrimarySensitivityReanalysis":False,
        }
    return {
      "sourceIdentity":"EXACT_TRIAL_SECONDARY_ECHOCARDIOGRAPHY_ARTICLE",
      "isFinalLockedPrimarySap":False,
      "isPrimarySensitivityReanalysis":False
    }

def hash_receipt(value):
    data={k:v for k,v in value.items() if k!="receiptSha256"}
    return sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode())

def audit(*,fetcher=fetch_public,at=None,commit=None,run=None):
    at=at or datetime.now(timezone.utc)
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError("UTC_AWARE_TIME_REQUIRED")
    checked=at.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
    outputs=[]
    article={"sourceIdentity":"UNVERIFIED"}
    responder={"sourceIdentity":"UNVERIFIED"}
    echo={"sourceIdentity":"UNVERIFIED"}
    for id,url in SOURCES.items():
        raw,status,error=fetcher(id)
        if raw is not None and not isinstance(raw,bytes):
            raise ValueError("INVALID_FETCHER_BYTES")
        row={"sourceId":id,"sourceUrl":url,"retrieval":status,
             "errorCategory":error,"responseSha256":sha256(raw) if raw else None,
             "responseBytes":len(raw) if raw else None}
        if status=="RETRIEVED" and raw:
            if id=="NEJM_ARTICLE_LANDING":
                article=article_landing(raw)
                row["documentIdentity"]=article["sourceIdentity"]
            elif id=="EUROPEPMC_RESPONDER_FULLTEXT":
                responder=europe_pmc_xml(raw,"RESPONDER")
                row["documentIdentity"]=responder["sourceIdentity"]
            else:
                echo=europe_pmc_xml(raw,"ECHO")
                row["documentIdentity"]=echo["sourceIdentity"]
        outputs.append(row)
    receipt={
        "schema":SCHEMA,"nct":NCT,"checkedAt":checked,
        "gitCommit":str(commit)[:64] if commit else None,
        "workflowRun":str(run)[:64] if run else None,
        "sources":outputs,
        "publisherSupplementListings":article,
        "supportiveSecondaryResponderMethods":responder,
        "secondaryEchoResearch":echo,
        "finalLockedPrimarySapAuthenticated":False,
        "primaryEndpointSensitivityRecalculated":False,
        "hfSafety11vs1Vs12vs3Reconciled":False,
        "signedClinicalGrades":0,
        "fdaPrediction":"ABSTAIN",
        "calibratedAccuracy":None,
        "nextResearchActions":[
          "Obtain authenticated final dated locked CY6033 primary statistical analysis plan and exact amendment history.",
          "Obtain full primary efficacy missingness, intercurrent event and sensitivity tables, not just responder secondary analysis.",
          "Reconcile the secondary and sponsor HF SAE event definitions, time windows, severity and analysis populations.",
          "Use sponsor data-request policy only under its stated eligibility/review conditions; no external request sent by this audit."
        ],
        "interpretation":"Source reachability and secondary methodology disclosures are evidence leads. A linked protocol or prespecified responder analysis does not authenticate a final locked primary SAP, a full original sensitivity reanalysis or a clinical 0-5 grade."
    }
    receipt["receiptSha256"]=hash_receipt(receipt)
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",default="acacia-alternate-source-audit/receipt.json")
    args=p.parse_args()
    import os
    result=audit(commit=os.environ.get("GITHUB_SHA"),run=os.environ.get("GITHUB_RUN_ID"))
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "stage":"ACACIA_ALTERNATE_PUBLIC_RESEARCH",
      "status":"SOURCE_CHECK_COMPLETE","nct":NCT,
      "sources":{r["sourceId"]:r["retrieval"] for r in result["sources"]},
      "article":result["publisherSupplementListings"],
      "responder":result["supportiveSecondaryResponderMethods"],
      "finalLockedPrimarySapAuthenticated":False,
      "clinicalGrades":0,
      "fdaPrediction":"ABSTAIN",
      "receiptSha256":result["receiptSha256"]
    },sort_keys=True))
if __name__=="__main__":
    main()
