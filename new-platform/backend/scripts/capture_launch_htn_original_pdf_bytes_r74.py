#!/usr/bin/env python3
"""MAIN R74: bounded original Launch-HTN PDF byte collection and research receipts.

Source-only research. Printed/internal dates NEVER prove prospectively signed
SAPs, original first-publication, FDA benefit-risk review or forecasts.
Do not archive/distribute copyrighted document bytes in public CI artifacts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from verify_focus_r73_launch_htn_document_index import validate
MAX_PDF_BYTES=12_000_000
MAX_PAGES=600
SOURCE_HOST="pmc.ncbi.nlm.nih.gov"
RECEIPT_SCHEMA="MAIN_R74_LAUNCH_HTN_ORIGINAL_PDF_BYTE_RECEIPTS_RESEARCH_ONLY"

def fetch_bounded(url:str, timeout:float=24.0)->tuple[bytes,str]:
    parsed=urllib.parse.urlsplit(url)
    if parsed.scheme!="https" or parsed.hostname!=SOURCE_HOST or parsed.port is not None:
        raise ValueError("SOURCE_URL_NOT_ALLOWLISTED")
    request=urllib.request.Request(url,headers={
        "User-Agent":"PDUFA-Command-Center-Research/1.0 (public source integrity; no patient data)",
        "Accept":"application/pdf"
    })
    with urllib.request.urlopen(request,timeout=timeout) as response:
        final=urllib.parse.urlsplit(response.geturl())
        if final.scheme!="https" or final.hostname not in (SOURCE_HOST,"cdn.ncbi.nlm.nih.gov"):
            raise ValueError("UNAPPROVED_FINAL_SOURCE_HOST")
        length=response.headers.get("Content-Length")
        if length and int(length)>MAX_PDF_BYTES:
            raise ValueError("DOCUMENT_TOO_LARGE")
        buf=bytearray()
        while True:
            chunk=response.read(131072)
            if not chunk: break
            buf.extend(chunk)
            if len(buf)>MAX_PDF_BYTES:raise ValueError("DOCUMENT_TOO_LARGE")
        return bytes(buf),response.geturl()

def review_pdf(data:bytes)->dict:
    if not data.startswith(b"%PDF-"):
        raise ValueError("RESPONSE_NOT_A_PDF")
    if len(data)<256 or len(data)>MAX_PDF_BYTES:
        raise ValueError("PDF_SIZE_INVALID")
    from pypdf import PdfReader
    reader=PdfReader(io.BytesIO(data),strict=True)
    pages=len(reader.pages)
    if not 1<=pages<=MAX_PAGES:
        raise ValueError("PDF_PAGES_INVALID")
    # Neither any embedded /CreationDate nor printed headings authenticate
    # original publication, protocol signatures, plan lock or data unblinding.
    return {"sourcePdfSha256":hashlib.sha256(data).hexdigest(),
        "sourcePdfByteCount":len(data),"pdfPageCount":pages,
        "sourcePdfMagicAndStructureValid":True,
        "internalAuthorshipAndProspectiveDateProven":False,
        "originalFirstPublicAvailabilityProven":False,
        "signedBeforeUnblindingProven":False}

def process(manifest:dict, r71:dict, getter=fetch_bounded)->dict:
    summary=validate(manifest,r71) # R73 exact NCT, 7 named paths, and no-grade locks.
    records=[]
    for document in manifest["documents"]:
        receipt={"supplementNumber":document["supplementNumber"],
                 "role":document["role"],"filename":document["filename"],
                 "sourceUrl":document["publicOriginalIndexLink"]}
        try:
            raw,final=getter(receipt["sourceUrl"])
            # No PDF bytes, filenames from HTTP headers or full article text are stored
            # in the public research receipt: hashes and page counts only.
            receipt.update(review_pdf(raw))
            receipt["retrievalStatus"]="SOURCE_PDF_BYTES_CAPTURED_IN_EPHEMERAL_RUNNER"
            receipt["observedFinalUrl"]=final
        except (urllib.error.URLError,urllib.error.HTTPError,ValueError,
                TimeoutError, OSError) as exc:
            # Explicit access failure / malformed file, not scientific absence.
            if isinstance(exc,urllib.error.HTTPError):
                code="HTTP_"+str(exc.code)
            elif isinstance(exc,(urllib.error.URLError,TimeoutError,OSError)):
                code="SOURCE_ACCESS_FAILED"
            else:
                code=str(exc)
            receipt["retrievalStatus"]="NOT_VERIFIED"
            receipt["failureCode"]=code[:90]
        except Exception:
            # Parsing errors from an unexpected PDF must fail closed, not crash the
            # seven-case source report into an apparent complete/positive result.
            receipt["retrievalStatus"]="NOT_VERIFIED"
            receipt["failureCode"]="PDF_READER_FAILED"
        records.append(receipt)
    verified=sum(x["retrievalStatus"]=="SOURCE_PDF_BYTES_CAPTURED_IN_EPHEMERAL_RUNNER" for x in records)
    return {"schema":RECEIPT_SCHEMA,
        "capturedAtUtc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "nct":"NCT06153693","originalIndexedSourceCount":summary["indexedSourceDocumentLinks"],
        "actualSourcePdfByteReceipts":verified,
        "sourceDocumentsUnverified":7-verified,
        "status":"ALL_PDF_BYTES_CAPTURED_RESEARCH_ONLY" if verified==7 else "PARTIAL_SOURCE_CAPTURE",
        "records":records,
        "rawPdfBytesArchivedInPublicArtifact":False,
        "independentlyAuthenticatedHistoricalFirstPublicDates":0,
        "independentlyAuthenticatedProspectiveSapSignatures":0,
        "signedScientificReviews":0,"validatedFDAForecasts":0,
        "clinicalGrade":None,"futureFDAOutcome":"ABSTAIN",
        "futureReviewTiming":"UNKNOWN","productionOrTrainingWrites":False}

def main()->None:
    arg=argparse.ArgumentParser()
    arg.add_argument("--manifest",default="new-platform/frontend/data/focus-r73-launch-htn-original-document-index.json")
    arg.add_argument("--r71",default="new-platform/frontend/data/focus-r71-five-main-publication-source-review.json")
    arg.add_argument("--output",required=True)
    args=arg.parse_args()
    out=process(json.loads(Path(args.manifest).read_text()),
                json.loads(Path(args.r71).read_text()))
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"status":out["status"],
                      "indexed":out["originalIndexedSourceCount"],
                      "pdfByteReceipts":out["actualSourcePdfByteReceipts"],
                      "sourceGaps":out["sourceDocumentsUnverified"],
                      "signedSapChronology":0,"fdaForecast":"ABSTAIN"},
                     sort_keys=True))

if __name__=="__main__":main()
