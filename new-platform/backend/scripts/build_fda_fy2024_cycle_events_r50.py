#!/usr/bin/env python3
"""MAIN R50: exact PDF-page FDA FY2024 *approved application* cycle-action evidence.

Only the source paper's Appendix A is considered. Every event is anchored by
page and text-word position. Source data are POSTDECISION and APPROVAL-SELECTED:
never expose to clinical forecasting, calibrate FDA probabilities, or treat event
rows as distinct application cycles. No application/NCT IDs are present here.
"""
from __future__ import annotations
import argparse,hashlib,json,collections
from datetime import datetime,timezone
from pathlib import Path
import fitz

SOURCE_URL="https://www.fda.gov/media/188188/download?attachment="
ORIGINAL_PDF_SHA256="589f432a7bb34237b247c1c39376ca1a3a9722984856f409e79d81fddf8127c4"
PAGES=range(83,95)     # zero-indexed PDF pages; printed Appendix A pages A-2 through A-13
CYCLES={"First":1,"Second":2,"Third":3,"Fourth":4,"Fifth":5,"Sixth":6}
ACTIONS={"AP":"APPROVAL","CR":"COMPLETE_RESPONSE","TA":"TENTATIVE_APPROVAL",
         "AE":"APPROVABLE_HISTORICAL","NA":"NOT_APPROVABLE_HISTORICAL","WD":"WITHDRAWN"}

def derive_page_events(words:list[tuple],page_index:int)->list[dict]:
    if not isinstance(page_index,int) or not 83<=page_index<=94:
        raise ValueError("SOURCE_TABLE_PAGE_OUT_OF_APPROVED_ONLY_APPENDIX")
    labels=[]
    actions=[]
    for item in words:
        if not isinstance(item,(tuple,list)) or len(item)<5:
            raise ValueError("MALFORMED_PDF_WORD_COORDINATE")
        x,y,_,_,value=item[:5]
        if not isinstance(value,str) or not isinstance(x,(int,float)) or not isinstance(y,(int,float)):
            raise ValueError("MALFORMED_PDF_WORD_COORDINATE")
        # Independent fixed, visually verified table-column windows. Headers,
        # prose/footer and section definitions outside the table are excluded.
        if 300<x<430 and value in CYCLES and 105<=y<=690:
            labels.append((float(y),value))
        if 425<x<490 and value in ACTIONS and 105<=y<=690:
            actions.append((float(x),float(y),value))
    if not actions or len(actions)!=len(labels):
        raise ValueError("REGULATORY_CYCLE_AND_ACTION_ROW_CARDINALITY_MISMATCH")
    results=[]
    matched_y=set()
    for x,y,code in actions:
        pairs=[(cy,word) for cy,word in labels if abs(cy-y)<3.0]
        if len(pairs)!=1 or pairs[0][0] in matched_y:
            raise ValueError("AMBIGUOUS_FDA_CYCLE_ACTION_ROW_ALIGNMENT")
        cy,word=pairs[0]
        matched_y.add(cy)
        results.append({
          "pdfPageOneBased":page_index+1,
          "pdfWordX0":round(x,2),"pdfWordY0":round(y,2),
          "printedFdaCycleOrdinal":CYCLES[word],
          "originalFdaAppendixActionCode":code,
          "originalFdaAppendixActionMeaning":ACTIONS[code],
          "regulatorApplicationNumber":None,
          "regulatorOriginalSubmissionNumber":None,
          "regulatorActionDate":None,
          "exactNctIds":[],
          "sourceWasLimitedToApplicationsApprovedInFy2024":True,
          "caseReviewedAndIdentityAdjudicated":False,
          "eligibleForHistoricalFDAForecastAccuracy":False,
          "qualifiedOriginalAsPublishedPredecisionTrialEvidence":False
        })
    return results

def extract(pdf:bytes,observed:str)->dict:
    if (not isinstance(pdf,bytes) or len(pdf)<50_000 or len(pdf)>45_000_000 or
        not pdf.startswith(b"%PDF") or
        hashlib.sha256(pdf).hexdigest()!=ORIGINAL_PDF_SHA256):
        raise ValueError("FDA_ORIGINAL_REPORT_SOURCE_SHA_MISMATCH")
    doc=fitz.open(stream=pdf,filetype="pdf")
    if len(doc)!=128:raise ValueError("FDA_REPORT_PAGE_COUNT_SOURCE_MISMATCH")
    events=[]
    for i in PAGES:
        page=doc[i]
        txt=page.get_text("text")
        if "Appendix A" not in txt:
            raise ValueError("EXPECTED_FDA_APPENDIX_A_PAGE_NOT_FOUND")
        events.extend(derive_page_events(page.get_text("words"),i))
    counts=collections.Counter(x["originalFdaAppendixActionCode"] for x in events)
    ords=collections.Counter(x["printedFdaCycleOrdinal"] for x in events)
    # Pinned official PDF's independent page/column extraction sanity checks.
    # If the document is revised, stop and re-adjudicate rather than auto-retune.
    if len(events)!=186 or dict(counts)!={"AP":126,"CR":43,"TA":17} or dict(ords)!={1:133,2:38,3:12,4:3}:
        raise ValueError("FDA_PDF_CYCLE_ACTION_TOTALS_CHANGED_NEEDS_SOURCE_REVIEW")
    return {
      "schema":"MAIN_R50_ORIGINAL_FDA_FY2024_APPROVED_CYCLE_ACTION_TABLE",
      "sourceReportUrl":SOURCE_URL,
      "sourceOriginalPdfSha256":ORIGINAL_PDF_SHA256,
      "sourcePdfPagesOneBased":[i+1 for i in PAGES],
      "sourceReportPageCount":len(doc),
      "observedUtc":observed,
      "scope":"FDA_FY2024_APPROVED_APPLICATIONS_ONLY",
      "sourceTableActionEvents":len(events),
      "sourceActionCounts":dict(sorted(counts.items())),
      "sourceCycleOrdinalCounts":{str(k):v for k,v in sorted(ords.items())},
      "sourceEvents":events,
      "sourceActionExtractionVerifiedByAutomatedRowAlignment":True,
      "independentHumanReviewOfApplicationCycleAssignments":False,
      "regulatorApplicationIdsReconciled":0,
      "originalNdaBlaReceiptCohortComplete":False,
      "notYetApprovedWithdrawnOrPendingFilingCohortIncluded":False,
      "modelEligibleIndependentHistoricalCases":0,
      "trueIndependentHistoricalBacktests":0,
      "measuredAccuracy":None,"calibratedApprovalProbability":None,
      "outcomeSideArtifactOnly":True,
      "forecasterInputAuthorized":False,
      "automaticClinicalGradesWritten":False,
      "productionStateMutated":False,
      "caution":"The 186 action events are row-level cycle actions from FDA's 2024 approved-application appendix, NOT 186 distinct applications or complete FDA original filing cohort. 43 CR actions occurred in applications later approved; all dates and original application/NCT identities remain unverified in this extraction. No retrospective prediction or calibrated performance is claimed."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pdf",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if not a.pdf.is_file() or a.pdf.is_symlink() or a.output.exists() or not a.output.parent.is_dir():
        raise ValueError("ORIGINAL_IMMUTABLE_SOURCE_REQUIRED")
    report=extract(a.pdf.read_bytes(),datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with a.output.open("xb") as f:f.write((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:report[k] for k in (
      "sourceOriginalPdfSha256","sourceTableActionEvents",
      "sourceActionCounts","sourceCycleOrdinalCounts","modelEligibleIndependentHistoricalCases",
      "trueIndependentHistoricalBacktests","measuredAccuracy"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
