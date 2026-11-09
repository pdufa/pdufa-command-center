#!/usr/bin/env python3
"""MAIN R56 source-anchored Savara IMPALA-2 protocol/SAP reconciliation queue.

The current publicly attached NCT04544293 protocol is v10, dated 2024-10-09;
its SAP is v1, dated 2024-04-24. We only verify exact original PDF bytes and
bounded page-local phrases, then emit explicitly labeled REVIEW LEADS. Neither
the document dates nor an apparent discrepancy establish unblinding chronology,
trial success, multiplicity failure, regulator outcome, or FDA probability.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import fitz

NCT="NCT04544293"
APP="svra-molgramostim"
PROT="NCT04544293-Prot_000.pdf"
SAP="NCT04544293-SAP_001.pdf"
EXPECTED={
 PROT:{"sha256":"0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849",
       "date":"2024-10-09","pages":134,"type":"PROTOCOL_CURRENT_ATTACHED_VERSION_10"},
 SAP:{"sha256":"2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888",
      "date":"2024-04-24","pages":89,"type":"SAP_CURRENT_ATTACHED_VERSION_1"}
}
# Page indices are *one-based PDF physical pages*, not printed footer pages.
# Every lead requires both a source-dated document and literal page-local text.
ITEMS=(
 ("DLCO_MANEUVER_AVERAGING_RULE","PRIMARY_ENDPOINT_MEASUREMENT","RECONCILIATION_REQUIRED",
   ((PROT,51,"average of the two best efforts"),
    (SAP,12,"average of all acceptable efforts"),
    (SAP,65,"average of the two best efforts"))),
 ("MULTIPLICITY_SCHEMATIC_AND_HOCHBERG","TYPE_I_ERROR_CONTROL","RECONCILIATION_REQUIRED",
   ((PROT,70,"alpha-splitting"),
    (SAP,25,"alpha splitting"),
    (SAP,65,"hypothesis testing schematic"))),
 ("FAS_AND_SAFETY_ANALYSIS_POPULATIONS","ESTIMAND_AND_SAFETY_POPULATIONS","PAGE_CITED_ALIGNMENT_LEAD",
   ((PROT,70,"safety analysis set"),
    (SAP,24,"full analysis set"),
    (SAP,24,"safety analysis set"))),
 ("PRIMARY_WEEK24_DLCO_MODEL","PRIMARY_STATISTICAL_METHOD","PAGE_CITED_ALIGNMENT_LEAD",
   ((PROT,73,"mixed model for repeated measurements"),
    (SAP,27,"mixed model for repeated measurements"))),
 ("CONTROL_BASED_MISSING_DATA","INTERCURRENT_EVENT_AND_IMPUTATION","PAGE_CITED_ALIGNMENT_LEAD",
   ((PROT,74,"control-based"),
    (SAP,27,"control-based imputation"))),
 ("SAFETY_ADR_VS_TREATMENT_RELATED_AE","SAFETY_DEFINITION","RECONCILIATION_REQUIRED",
   ((SAP,65,"frequency of serious ADRs"),
    (SAP,65,"serious treatment-related AEs"))),
 ("EQ5D_INDEX_VS_DOMAIN_SUMMARIES","SECONDARY_EXPLORATORY_METHODS","RECONCILIATION_REQUIRED",
   ((SAP,65,"5-digit value"),
    (SAP,65,"within the 5 domains"))),
 ("HOSPITALIZATION_EXPLORATORY_ENDPOINT_REMOVED","EXPLORATORY_ENDPOINT_CHANGES","RECONCILIATION_REQUIRED",
   ((SAP,65,"number of hospitalizations"),
    (SAP,65,"was removed"))),
 ("OXYGEN_REST_DURATION_ASSUMPTION","EXPLORATORY_ENDPOINT_DERIVATION","RECONCILIATION_REQUIRED",
   ((SAP,65,"960 minutes"),
    (SAP,65,"24 hours per day"))),
 ("SAP_PROTOCOL_DOCUMENT_VERSION_ORDER","DOCUMENT_VERSION_CHRONOLOGY","DOCUMENT_DATES_NOT_FIRST_PUBLIC",
   ((PROT,2,"09 October 2024"),
    (SAP,1,"24APR2024"))),
)
MAX_PDF=55_000_000

def page_match(raw:bytes,filename:str):
    if not raw.startswith(b"%PDF-"):raise ValueError("ORIGINAL_SOURCE_NOT_PDF")
    pdf=fitz.open(stream=raw,filetype="pdf")
    expected=EXPECTED[filename]
    if pdf.needs_pass or pdf.is_encrypted or len(pdf)!=expected["pages"]:
        raise ValueError("ORIGINAL_VERIFIED_PDF_PAGE_COUNT_DRIFT")
    required={page for _,_,_,evidence in ITEMS for doc,page,phrase in evidence if doc==filename}
    text={}
    for page in required:
        if not 1<=page<=len(pdf):raise ValueError("INVALID_PHYSICAL_PDF_PAGE")
        value=" ".join(pdf[page-1].get_text("text",sort=True).split())
        if not value or len(value)>230000:raise ValueError("UNREADABLE_OR_OVERSIZED_SOURCE_PAGE")
        text[page]=value
    return text

def _excerpt(text,phrase):
    pos=text.casefold().find(phrase.casefold())
    if pos<0:raise ValueError("VERIFIED_SAVARA_SOURCE_PHRASE_NO_LONGER_ON_EXPECTED_PAGE")
    return " ".join(text[max(0,pos-75):min(len(text),pos+len(phrase)+95)].split())[:230]

def build(raw_map:dict[str,bytes],r53:dict,r54:dict,r55:dict):
    if (not isinstance(r53,dict) or r53.get("schema")!="MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH" or
        r53.get("nctRosterCount")!=29 or r53.get("applicationGroupCount")!=23 or
        r53.get("originalPdfBodiesRetrieved")!=23 or
        len(r53.get("documentResearch",[]))!=23 or
        r53.get("validatedFDAForecasts")!=0 or
        not isinstance(r54,dict) or r54.get("schema")!="MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX" or
        r54.get("canonicalTrials")!=29 or r54.get("applicationGroups")!=23 or
        len(r54.get("trialMethodsReview",[]))!=29 or
        len(r54.get("applicationMethodsReview",[]))!=23 or
        r54.get("independentlyValidatedApplicationFdaPredictions")!=0 or
        not isinstance(r55,dict) or r55.get("schema")!="MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS" or
        r55.get("nctTrials")!=29 or r55.get("applicationGroups")!=23 or
        r55.get("sourceVerifiedCurrentProtocolSAPDocuments")!=23 or
        len(r55.get("originalUniqueTrialEvidence",[]))!=29 or
        len(r55.get("currentSourceCasePackets",[]))!=23 or
        r55.get("independentlyValidatedFDAApplicationForecasts")!=0 or
        r55.get("clinicalOrProductionWrites") is not False):
        raise ValueError("UNQUALIFIED_R53_R54_R55_ORIGINAL_SOURCE_CHAIN")
    source_docs={d.get("archivedPdfFilename"):d for d in r53["documentResearch"] if d.get("nct")==NCT}
    if set(source_docs)!=set(EXPECTED) or set(raw_map)!=set(EXPECTED):
        raise ValueError("EXACT_ORIGINAL_SAVARA_PROTOCOL_SAP_PAIR_REQUIRED")
    if len([x for x in r54["trialMethodsReview"] if x.get("nct")==NCT])!=1 or not any(
        x.get("applicationCycleId")==APP and x.get("exactNcts")==[NCT]
        for x in r55["currentSourceCasePackets"]):
        raise ValueError("SAVARA_CYCLE_NOT_IN_EXACT_29_23_RESEARCH")
    docs=[]
    p_text={}
    for filename in (PROT,SAP):
        record=source_docs[filename]
        expectation=EXPECTED[filename]
        raw=raw_map[filename]
        if record.get("sourceUrl")!=(
            "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/"+filename
        ):
            raise ValueError("SAVARA_DOCUMENT_SOURCE_URL_NOT_ORIGINAL")
        if (not isinstance(raw,bytes) or not 100<len(raw)<=MAX_PDF or
            hashlib.sha256(raw).hexdigest()!=expectation["sha256"] or
            len(raw)!=record.get("sourceBytes") or
            record.get("sourceSha256")!=expectation["sha256"] or
            record.get("currentRegistryDocumentDate")!=expectation["date"] or
            record.get("retrievalStatus")!="FETCHED" or
            record.get("pdfResearch",{}).get("pageCount")!=expectation["pages"]):
            raise ValueError("SAVARA_EXACT_SOURCE_BYTES_OR_DATE_RECEIPT_MISMATCH")
        p_text[filename]=page_match(raw,filename)
        docs.append({"file":filename,"originalSha256":expectation["sha256"],
            "currentRegistryDocumentDate":expectation["date"],
            "documentRole":expectation["type"],"sourceUrl":record["sourceUrl"],
            "firstPublicPostingDateIndependentlyVerified":False,
            "preUnblindingDatabaseLockAndApprovalDateVerified":False})
    items=[]
    for code,domain,state,leads in ITEMS:
        excerpts=[{"filename":file,"pdfPageOneBased":page,"literalSourcePhrase":phrase,
          "pageTextExcerpt":_excerpt(p_text[file][page],phrase)}
          for file,page,phrase in leads]
        items.append({"id":code,"domain":domain,"reviewClass":state,
          "sourceLeads":excerpts,
          "clinicalMaterialityAdjudicated":False,
          "originalAmendmentChainVerified":False,
          "statisticalProtocolConsistencyReviewedAndSigned":False,
          "FDAOutcomeInferenceAuthorized":False})
    if len({item["id"] for item in items})!=len(items):raise ValueError("DUPLICATE_REVIEW_EXCEPTION_ID")
    return {
      "schema":"MAIN_R56_SAVARA_SOURCE_PAGE_VERSUS_SAP_RECONCILIATION_QUEUE",
      "builtAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nct":NCT,"applicationCycleId":APP,"original29NctRosterPreserved":True,
      "original23ApplicationGroupsPreserved":True,
      "verifiedCurrentPublicDocuments":docs,
      "pageAnchoredSourceReviewItems":items,
      "totalReviewItems":len(items),
      "explicitDiscrepancyReconciliationItems":sum(
          x["reviewClass"]=="RECONCILIATION_REQUIRED" for x in items),
      "currentVersionDateChronologyFlag":True,
      "independentSignedStatisticalReviewCount":0,
      "preReadoutOriginalSignedSapVersionsVerified":0,
      "currentRegistryResultPValuesIndependentlyRecalculated":0,
      "FDARegulatorCMCReviewVerified":False,
      "independentlyValidatedApplicationFDAForecasts":0,
      "historicalIndependentPredictionBacktests":0,
      "measuredApprovalPredictionAccuracy":None,
      "officialFDAOutcomePrediction":"ABSTAIN",
      "approvalProbability":None,
      "noModelTrainingClinicalOrProductionWrites":True,
      "warning":"These current document page-linked observations are not signed original pre-unblinding protocol/SAP versions. A reported difference does not alone establish post-hoc changes, FDA rejection, efficacy failure or probability."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r53",required=True,type=Path)
    p.add_argument("--r54",required=True,type=Path)
    p.add_argument("--r55",required=True,type=Path)
    p.add_argument("--pdf-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if (a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir() or
        not a.pdf_dir.is_dir() or a.pdf_dir.is_symlink()):
        raise ValueError("NO_SAFE_WRITE_ONCE_VERIFIED_ORIGINAL_PDF_OUTPUT")
    def load(path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size>20_000_000:
            raise ValueError("UNTRUSTED_ORIGINAL_RESEARCH_REPORT_INPUT")
        return json.loads(path.read_bytes())
    raw={}
    for filename in EXPECTED:
        path=a.pdf_dir/filename
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(a.pdf_dir.resolve()):
            raise ValueError("SAVARA_ORIGINAL_PDF_NOT_AVAILABLE")
        raw[filename]=path.read_bytes()
    report=build(raw,load(a.r53),load(a.r54),load(a.r55))
    with a.output.open("xb") as f:f.write((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    print(json.dumps({x:report[x] for x in (
      "nct","applicationCycleId","totalReviewItems",
      "explicitDiscrepancyReconciliationItems","preReadoutOriginalSignedSapVersionsVerified",
      "independentlyValidatedApplicationFDAForecasts")},sort_keys=True))

if __name__=="__main__":main()
