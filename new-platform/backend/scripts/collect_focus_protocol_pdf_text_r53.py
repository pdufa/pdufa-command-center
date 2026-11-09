#!/usr/bin/env python3
"""MAIN R53: source-verified current registry protocol/SAP PDF *research* audit.

Uses exact filenames and NCTs from independently captured R46 public
ClinicalTrials.gov large-document metadata, never guesses or searches for
private documents. Preserves downloaded PDF bytes + SHA and extracts
page-anchored keyword context for human protocol-versus-SAP review.
Document date != date of first public posting != prospective SAP lock.
No treatment effect, multiplicity correctness or FDA outcome is inferred.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
import fitz
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest

NCT=re.compile(r"NCT\d{8}\Z")
FILE=re.compile(r"(?:Prot|SAP|Prot_SAP)_[A-Za-z0-9_-]{1,36}\.pdf\Z")
KEYWORDS=(
    "primary endpoint","primary outcome","statistical analysis plan",
    "multiplicity","hierarchical testing","type i error","missing data",
    "interim analysis","intention-to-treat","intention to treat",
    "protocol amendment","version history","treatment-emergent",
    "adverse event","safety population","alpha"
)
MAX_BYTES=55_000_000
MAX_PAGES=1800
MAX_EXTRACT_PAGES=120
ALLOWED={"cdn.clinicaltrials.gov"}

class StrictPdfRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        p=urlsplit(newurl)
        if (p.scheme!="https" or p.hostname not in ALLOWED or p.username or p.password
            or p.port not in (None,443) or p.query or p.fragment):
            raise HTTPError(req.full_url,code,"DISALLOWED_PUBLIC_PDF_REDIRECT",headers,fp)
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def safe_documents(manifest,receipt):
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        receipt.get("schema")!="MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX" or
        receipt.get("nctCount")!=29 or receipt.get("applicationGroupCount")!=23 or
        len(receipt.get("records",[]))!=29):
        raise ValueError("EXACT_29_23_DOCUMENT_ROSTER_AND_RECEIPT_REQUIRED")
    canon={x["nct"] for x in manifest["trialRows"]}
    sources={}
    for row in receipt["records"]:
        if not isinstance(row,dict) or row.get("nct") not in canon or row["nct"] in sources:
            raise ValueError("DUPLICATE_OR_UNKNOWN_NCT_IN_SOURCE_RECEIPT")
        sources[row["nct"]]=row
    if set(sources)!=canon:raise ValueError("DOC_SOURCE_RECEIPT_NCTS_MISMATCH")
    cross={n:[] for n in canon}
    for g in manifest["applicationGroups"]:
        for n in g["ncts"]:cross[n].append(g["cycleId"])
    jobs=[]
    for nct in sorted(canon):
        row=sources[nct]
        if row.get("applicationCycleIds")!=cross[nct]:
            raise ValueError("SOURCE_PDF_DOCUMENT_WRONG_APPLICATION_CROSSWALK")
        attachments=row.get("currentDocumentIndex",[])
        if not isinstance(attachments,list) or len(attachments)>30:
            raise ValueError("MALFORMED_DOCUMENT_ATTACHMENT_INDEX")
        for item in attachments:
            name=item.get("filenameAsRegistry")
            if not isinstance(name,str) or not FILE.fullmatch(name):
                raise ValueError("UNTRUSTED_OR_NON_PROTOCOL_SAP_FILENAME")
            date=item.get("documentDateAsRegistry")
            if date is not None and (not isinstance(date,str) or
                                     not re.fullmatch(r"20\d{2}-\d\d-\d\d",date)):
                raise ValueError("UNVERIFIED_CURRENT_REGISTRY_DOCUMENT_DATE")
            if item.get("hasProtocolFlagAsRegistry") is not True and item.get("hasSapFlagAsRegistry") is not True:
                raise ValueError("NON_PROTOCOL_DOCUMENT_IN_RESEARCH_INDEX")
            jobs.append({"nct":nct,"filename":name,
                "currentRegistryDocumentDate":date,
                "hasProtocolFlag":item["hasProtocolFlagAsRegistry"],
                "hasSapFlag":item["hasSapFlagAsRegistry"],
                "applicationCycleIds":cross[nct],
                "sourceUrl":f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{name}"})
    if len({(x["nct"],x["filename"]) for x in jobs})!=len(jobs):
        raise ValueError("DUPLICATE_ORIGINAL_PDF_ATTACHMENT")
    return jobs

def public_fetch(url):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname not in ALLOWED or p.port not in (None,443)
        or p.query or p.fragment or p.username or p.password or
        not re.fullmatch(r"/large-docs/\d{2}/NCT\d{8}/(?:Prot|SAP|Prot_SAP)_[A-Za-z0-9_-]{1,36}\.pdf",p.path)):
        raise ValueError("NON_CANONICAL_CTG_PUBLIC_PDF_REQUEST")
    req=Request(url,headers={"Accept":"application/pdf",
          "User-Agent":"PDUFA-Focus-readonly-current-public-document-research/1.0"})
    try:
        with build_opener(StrictPdfRedirect()).open(req,timeout=24) as resp:
            if urlsplit(resp.geturl()).hostname not in ALLOWED:
                raise ValueError("UNTRUSTED_PUBLIC_PDF_REDIRECT")
            content_type=resp.headers.get("Content-Type","").split(";")[0].strip().lower()
            if content_type!="application/pdf":
                return {"status":"UNEXPECTED_PDF_CONTENT_TYPE","contentType":content_type},None
            raw=resp.read(MAX_BYTES+1)
            if not 100<=len(raw)<=MAX_BYTES:
                return {"status":"PDF_SOURCE_TOO_LARGE_OR_EMPTY","byteCount":len(raw)},None
            return {"status":"FETCHED","contentType":content_type,
                    "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)},raw
    except HTTPError as e:
        return {"status":"HTTP_UNAVAILABLE","httpStatus":e.code},None
    except (OSError,URLError,TimeoutError) as e:
        return {"status":"FETCH_BLOCKED","errorClass":type(e).__name__},None

def inspect_pdf(raw,nct):
    if not raw.startswith(b"%PDF-"):raise ValueError("NON_PDF_ORIGINAL_SOURCE")
    try:
        doc=fitz.open(stream=raw,filetype="pdf")
        if doc.needs_pass or doc.is_encrypted or not 1<=len(doc)<=MAX_PAGES:
            raise ValueError("ENCRYPTED_OR_MALFORMED_PUBLIC_PROTOCOL_PDF")
        snippets=[];nct_pages=[]
        top=[]
        for page_ix in range(min(len(doc),MAX_EXTRACT_PAGES)):
            text=doc[page_ix].get_text("text",sort=True)
            if len(text)>220_000:raise ValueError("OVERSIZED_PDF_PAGE_TEXT")
            if page_ix<4:top.append(text[:2800])
            if nct in text:nct_pages.append(page_ix+1)
            lower=text.casefold()
            for keyword in KEYWORDS:
                if sum(s["term"]==keyword for s in snippets)>=2:continue
                start=0
                index=lower.find(keyword,start)
                if index>=0:
                    excerpt=" ".join(text[max(0,index-90):min(len(text),index+len(keyword)+135)].split())
                    snippets.append({"term":keyword,"pdfPageOneBased":page_ix+1,
                        "sourceTextExcerpt":excerpt[:260]})
        first=" ".join(" ".join(top).split())[:1400]
        return {
          "pageCount":len(doc),"pagesWithTextChecked":min(len(doc),MAX_EXTRACT_PAGES),
          "nctMentionedInInspectedPages":bool(nct_pages),
          "nctMentionPageNumbers":nct_pages[:15],
          "keywordSourceExcerpts":snippets[:28],
          "frontMatterSourceExcerpt":first,
          "originalDocumentDatesAndSignatureIndependentlyAuthenticated":False,
          "sourceDocumentTextHumanReviewed":False,
          "statisticalPrespecificationValidated":False,
          "regulatoryConclusionAuthorized":False
        }
    except (RuntimeError,ValueError) as e:
        raise ValueError("UNUSABLE_PUBLIC_PROTOCOL_PDF_"+type(e).__name__)

def collect(manifest,receipt,fetcher,raw_dir):
    if not raw_dir.is_dir() or raw_dir.is_symlink() or any(raw_dir.iterdir()):
        raise ValueError("REQUIRES_EMPTY_IMMUTABLE_PDF_ARCHIVE")
    jobs=safe_documents(manifest,receipt)
    def one(item):
        status,raw=fetcher(item["sourceUrl"])
        if not isinstance(status,dict):raise ValueError("UNTRUSTED_PDF_SOURCE_RECEIPT")
        result={**item,"retrievalStatus":status.get("status"),
           "sourceHttpStatus":status.get("httpStatus"),
           "sourceContentType":status.get("contentType"),
           "sourceSha256":None,"sourceBytes":None,"pdfResearch":None,
           "originalSAPFirstPublicDateVerified":False,
           "originalPreUnblindingLockedVersionVerified":False,
           "clinicalGrade":None,"fdaForecast":"ABSTAIN"}
        if status.get("status")=="FETCHED":
            if not isinstance(raw,bytes) or len(raw)>MAX_BYTES or len(raw)<100:
                raise ValueError("FETCHED_ORIGINAL_PDF_BYTES_NOT_PRESENT")
            if status.get("bytes")!=len(raw) or status.get("sha256")!=hashlib.sha256(raw).hexdigest():
                raise ValueError("ORIGINAL_PUBLIC_PDF_SOURCE_SHA_MISMATCH")
            info=inspect_pdf(raw,item["nct"])
            result.update(sourceSha256=status["sha256"],sourceBytes=len(raw),pdfResearch=info)
        return result,raw
    rows=[]
    # Prioritize SVRA's actual attached protocol and SAP for near-term review.
    jobs.sort(key=lambda d:(0 if d["nct"]=="NCT04544293" else 1,d["nct"],d["filename"]))
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(one,item):item for item in jobs}
        for future in as_completed(futures):
            item=futures[future]
            result,raw=future.result()
            if raw is not None and result["sourceSha256"] is not None:
                path=raw_dir/(item["nct"]+"-"+item["filename"])
                with path.open("xb") as f:f.write(raw)
                result["archivedPdfFilename"]=path.name
            rows.append(result)
    rows.sort(key=lambda x:(x["nct"],x["filename"]))
    by_nct={}
    for row in rows:
        by_nct.setdefault(row["nct"],[]).append(row)
    app=[]
    for group in manifest["applicationGroups"]:
        documents=[r for n in group["ncts"] for r in by_nct.get(n,[])]
        app.append({
          "applicationCycleId":group["cycleId"],"ticker":group["ticker"],
          "exactNcts":list(group["ncts"]),
          "currentRegistryDocumentEntries":len(documents),
          "originalPublicPdfBodiesVerified":sum(r["sourceSha256"] is not None for r in documents),
          "currentProtocolPdfBodiesRetrieved":any(r["hasProtocolFlag"] and r["pdfResearch"] is not None for r in documents),
          "currentSapPdfBodiesRetrieved":any(r["hasSapFlag"] and r["pdfResearch"] is not None for r in documents),
          "originalPrespecifiedSAPFirstPublicBeforeTrialUnblinding":False,
          "originalEndpointHierarchyAndMultiplicityAdjudicated":False,
          "statisticalReviewerSigned":False,"scientificBenefitRiskValidated":False,
          "researchReviewState":"NEEDS_ORIGINAL_PRE_READOUT_SAP_AND_STATISTICAL_REVIEW",
          "officialFdaPrediction":"ABSTAIN","numericalProbability":None})
    return {
      "schema":"MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nctRosterCount":29,"applicationGroupCount":23,
      "currentRegistryDocumentEntries":len(rows),
      "trialNctsWithDocumentEntries":len(by_nct),
      "originalPdfBodiesRetrieved":sum(r["sourceSha256"] is not None for r in rows),
      "currentProtocolPdfBodiesRetrieved":sum(r["hasProtocolFlag"] and r["sourceSha256"] is not None for r in rows),
      "currentSapPdfBodiesRetrieved":sum(r["hasSapFlag"] and r["sourceSha256"] is not None for r in rows),
      "sourceOutcomes":{s:sum(r["retrievalStatus"]==s for r in rows)
          for s in sorted({x["retrievalStatus"] for x in rows})},
      "documentResearch":rows,"applicationResearch":app,
      "originalFirstPublicSAPDateVerified":0,
      "historicalRegisteredEndpointAmendmentChainVerified":0,
      "independentScientificGrades":0,"validatedFDAForecasts":0,
      "measuredApprovalAccuracy":None,"actualHistoricalBacktests":0,
      "trainingAuthorized":False,"clinicalOrProductionWrites":False,
      "officialFutureFDAOutcome":"ABSTAIN",
      "warning":"Current-registry PDF source bytes and keyword snippets are not a locked prospective analysis plan, independent endpoint/multiplicity adjudication or prediction. ClinicalTrials.gov results documents may be uploaded after study completion."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index",type=Path,required=True)
    parser.add_argument("--raw-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    a=parser.parse_args()
    if (a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir() or
        not a.index.is_file() or a.index.is_symlink() or a.index.stat().st_size>10_000_000):
        raise ValueError("ORIGINAL_SOURCE_INDEX_AND_WRITE_ONCE_RESEARCH_REPORT_REQUIRED")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    report=collect(manifest,json.loads(a.index.read_bytes()),public_fetch,a.raw_dir)
    with a.output.open("xb") as f:f.write((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps({k:report[k] for k in (
       "nctRosterCount","applicationGroupCount","currentRegistryDocumentEntries",
       "originalPdfBodiesRetrieved","currentProtocolPdfBodiesRetrieved",
       "currentSapPdfBodiesRetrieved","originalFirstPublicSAPDateVerified",
       "independentScientificGrades","validatedFDAForecasts"
    )},sort_keys=True))

if __name__=="__main__":main()
