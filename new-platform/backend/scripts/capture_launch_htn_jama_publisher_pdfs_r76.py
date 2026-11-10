#!/usr/bin/env python3
"""MAIN R76 official JAMA public supplementary PDF source-byte research fallback.

HTML page is public and supplement links are publisher-origin. Never log,
persist or reuse signed ephemeral CDN URLs. No authentication/CAPTCHA bypass.
No copyrighted PDF binary stored beyond ephemeral local memory.
"""
from __future__ import annotations
import argparse,datetime as dt,html,io,json,re,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path
from capture_launch_htn_original_pdf_bytes_r74 import review_pdf,MAX_PDF_BYTES
from verify_focus_r73_launch_htn_document_index import validate

ARTICLE="https://jamanetwork.com/journals/jama/fullarticle/2835763"
CDN_HOST="cdn.jamanetwork.com"
CDN_PREFIX="/ama/content_public/journal/jama/939665/"
RECEIPT_SCHEMA="MAIN_R76_JAMA_PUBLISHER_ORIGINAL_PDF_BYTES_RESEARCH_ONLY"

class Hrefs(HTMLParser):
    def __init__(self):
        super().__init__();self.items=[]
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="a":
            self.items.extend(v for k,v in attrs if k.lower()=="href" and v)

def validate_candidate_url(url):
    u=urllib.parse.urlsplit(html.unescape(url))
    if u.scheme!="https" or u.hostname!=CDN_HOST or u.port is not None or not u.path.startswith(CDN_PREFIX):
        return None
    m=re.fullmatch(r"/ama/content_public/journal/jama/939665/joi250041supp([1-7])_prod_[a-zA-Z0-9._-]+[.]pdf",u.path)
    if not m or not ("Expires=" in u.query and "Signature=" in u.query):
        return None
    return int(m.group(1)),u.geturl()

def extract_public_cdn_links(page_html:str)->dict[int,str]:
    if len(page_html)>3_000_000:raise ValueError("PUBLISHER_HTML_TOO_LARGE")
    parser=Hrefs();parser.feed(page_html)
    # Parse href values only, never arbitrary script-injected URLs or user input.
    urls={}
    for href in parser.items:
        parsed=validate_candidate_url(href)
        if parsed:
            n,u=parsed
            if n in urls and urls[n]!=u:
                raise ValueError("AMBIGUOUS_PUBLISHER_PDF_"+str(n))
            urls[n]=u
    return urls

def fetch_publisher_html(timeout=25.0)->str:
    req=urllib.request.Request(ARTICLE,headers={
        "User-Agent":"Mozilla/5.0 (compatible; public-source-research/1.0)",
        "Accept":"text/html"
    })
    with urllib.request.urlopen(req,timeout=timeout) as response:
        u=urllib.parse.urlsplit(response.geturl())
        if u.scheme!="https" or u.hostname!="jamanetwork.com":
            raise ValueError("ARTICLE_SOURCE_REDIRECT_NOT_ALLOWED")
        raw=response.read(3_000_001)
        if len(raw)>3_000_000:raise ValueError("PUBLISHER_HTML_TOO_LARGE")
        return raw.decode("utf-8",errors="replace")

def fetch_publisher_pdf(signed_url,timeout=24.0)->bytes:
    if not validate_candidate_url(signed_url):
        raise ValueError("CDN_URL_NOT_AUTHORIZED")
    req=urllib.request.Request(signed_url,headers={
       "User-Agent":"Mozilla/5.0 (compatible; public-source-research/1.0)",
       "Accept":"application/pdf"
    })
    with urllib.request.urlopen(req,timeout=timeout) as r:
        final=urllib.parse.urlsplit(r.geturl())
        if final.scheme!="https" or final.hostname!=CDN_HOST or final.port is not None:
            raise ValueError("CDN_REDIRECT_NOT_ALLOWED")
        if int(r.headers.get("Content-Length") or 0)>MAX_PDF_BYTES:
            raise ValueError("PDF_TOO_LARGE")
        return r.read(MAX_PDF_BYTES+1)

def process(manifest,r71,links_getter=fetch_publisher_html,pdf_getter=fetch_publisher_pdf):
    validate(manifest,r71)
    page_error=None;links={}
    try:
        links=extract_public_cdn_links(links_getter())
    except Exception as err:
        # No private token or signed URL should enter a public receipt/log.
        page_error=("PUBLISHER_ACCESS_FAILED" if not isinstance(err,ValueError)
                    else str(err)[:95])
    records=[]
    for d in manifest["documents"]:
        n=d["supplementNumber"]
        receipt={"supplementNumber":n,"filename":d["filename"],"role":d["role"],
                 "stableSourceLocator":ARTICLE,"retrievalStatus":"NOT_VERIFIED"}
        if n not in links:
            receipt["failureCode"]=page_error or "PUBLISHER_SUPPLEMENT_LINK_NOT_PRESENT"
        else:
            try:
                data=pdf_getter(links[n])
                receipt.update(review_pdf(data))
                receipt["retrievalStatus"]="PUBLISHER_ORIGINAL_PDF_BYTE_HASH_CAPTURED"
                receipt["sourceHost"]=CDN_HOST
            except Exception as err:
                receipt["failureCode"]=("SOURCE_ACCESS_FAILED" if not isinstance(err,ValueError)
                                        else str(err)[:95])
        records.append(receipt)
    retrieved=sum(d["retrievalStatus"]=="PUBLISHER_ORIGINAL_PDF_BYTE_HASH_CAPTURED" for d in records)
    return {"schema":RECEIPT_SCHEMA,
      "capturedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "nct":"NCT06153693","publisherOriginalArticle":ARTICLE,
      "sourceLinksInPublicArticle":len(links),
      "pdfSourceByteHashReceipts":retrieved,"unverifiedPdfSources":7-retrieved,
      "status":"ALL_SEVEN_SOURCE_BYTES_CAPTURED_RESEARCH_ONLY" if retrieved==7 else "SOURCE_ACCESS_INCOMPLETE",
      "records":records,
      "signedCdnUrlsRetained":False,"copyrightedPdfBytesArchived":False,
      "authenticatedOriginalFirstPublicPdfDates":0,
      "authenticatedPreUnblindingSapLocks":0,
      "independentClinicalSignatures":0,
      "validatedFDAForecasts":0,"clinicalGrade":None,
      "futureFDAOutcome":"ABSTAIN","futureTiming":"UNKNOWN",
      "productionOrModelTrainingWrites":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",default="new-platform/frontend/data/focus-r73-launch-htn-original-document-index.json")
    p.add_argument("--r71",default="new-platform/frontend/data/focus-r71-five-main-publication-source-review.json")
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=process(json.loads(Path(a.manifest).read_text()),json.loads(Path(a.r71).read_text()))
    f=Path(a.output);f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    for d in report["records"]:
        print("R76_SOURCE_STATUS",d["filename"],d["retrievalStatus"],d.get("failureCode","PDF_SHA256_VERIFIED"))
    print(json.dumps({"status":report["status"],"publisherLinks":report["sourceLinksInPublicArticle"],
       "pdfHashes":report["pdfSourceByteHashReceipts"],"unverified":report["unverifiedPdfSources"],
       "FDAOutcome":"ABSTAIN","preUnblindingSignedLock":0},sort_keys=True))

if __name__=="__main__":main()
