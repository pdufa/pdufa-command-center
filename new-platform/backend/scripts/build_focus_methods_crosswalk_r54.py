#!/usr/bin/env python3
"""MAIN R54: page-cited protocol-versus-SAP methods EVIDENCE matrix, not grades.

Read only original SHA-verified public attached PDFs and original present-day
registry snapshots already archived by R53. Eight scientific review dimensions
identify textual leads for human adjudication across all 29 FOCUS NCTs and 23
application groups. A keyword/phrase hit IS NOT statistical prespecification,
scientific correctness or evidence a study succeeded. Absence of a machine-
readable hit IS NOT evidence the method is missing or inappropriate.
"""
from __future__ import annotations
import argparse,hashlib,json,re,unicodedata
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import fitz
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest

DOMAINS={
 "PRIMARY_ENDPOINT":("primary endpoint","primary efficacy endpoint","primary outcome",
                     "primary efficacy analysis"),
 "ESTIMAND_ANALYSIS_POPULATION":("estimand","full analysis set","intention to treat",
                     "intent-to-treat","intention-to-treat","modified intent",
                     "analysis population","per-protocol set"),
 "STATISTICAL_MODEL":("analysis of covariance","mixed model","logistic regression",
                     "repeated measurements","regression model","hazard ratio",
                     "stratified test","generalized estimating"),
 "MULTIPLICITY_CONTROL":("multiplicity","hochberg","holm procedure",
                     "hierarchical testing","alpha splitting","alpha-splitting",
                     "sequential testing","type i error","family-wise"),
 "MISSING_DATA_INTERCURRENT_EVENTS":("missing data","multiple imputation",
                     "intercurrent event","control-based imputation",
                     "non-responder imputation","treatment policy","rescue medication"),
 "SENSITIVITY_ANALYSIS":("sensitivity analyses","sensitivity analysis",
                     "tipping point","supplementary analyses","robustness"),
 "ADVERSE_EVENTS_SAFETY":("treatment-emergent adverse","serious adverse event",
                     "adverse events","safety population","safety analyses",
                     "adverse event"),
 "PROTOCOL_SAP_VERSION_CHANGES":("protocol amendment","amendment history",
                     "summary of changes","changes to the protocol",
                     "changes from the protocol","deviations from the protocol",
                     "version history","protocol deviations")
}
MAX_PDF_BYTES=55_000_000
MAX_PAGES=1800
MAX_PAGE_TEXT=230_000
MAX_EXCERPT=225
MAX_REVIEW_PAGES=700
SHA_RE=re.compile(r"[a-f0-9]{64}\Z")
NAME_RE=re.compile(r"NCT\d{8}-(?:Prot|SAP|Prot_SAP)_[A-Za-z0-9_-]{1,36}\.pdf\Z")

def clean(s):
    if not isinstance(s,str):raise ValueError("INVALID_METHOD_SOURCE_TEXT")
    s=unicodedata.normalize("NFKC",s)
    return " ".join(s.casefold().split())

def _phrase_hits(text:str,phrase:str):
    normalized=clean(phrase)
    return list(re.finditer(r"(?<![\w])"+re.escape(normalized)+r"(?![\w])",text))

def inspect(raw:bytes,nct:str,registry_outcomes:list[dict]):
    if not raw.startswith(b"%PDF-"):
        raise ValueError("NOT_ORIGINAL_PDF_SOURCE")
    doc=fitz.open(stream=raw,filetype="pdf")
    if doc.needs_pass or doc.is_encrypted or not 1<=len(doc)<=MAX_PAGES:
        raise ValueError("UNTRUSTED_OR_ENCRYPTED_PDF")
    found={name:[] for name in DOMAINS}
    exact=[[] for _ in registry_outcomes]
    searchable=0
    for page_ix in range(min(len(doc),MAX_REVIEW_PAGES)):
        text=" ".join(doc[page_ix].get_text("text",sort=True).split())
        if len(text)>MAX_PAGE_TEXT:raise ValueError("EXCESSIVE_PDF_PAGE_TEXT")
        if not text:continue
        searchable+=1
        lower=clean(text)
        for category,phrases in DOMAINS.items():
            if len(found[category])>=3:continue
            matches=[]
            for phrase in phrases:
                hit=_phrase_hits(lower,phrase)
                if hit:matches.append((hit[0].start(),phrase,hit[0].end()))
            if matches:
                loc,phrase,end=min(matches,key=lambda q:q[0])
                # Index pages are allowed as leads, not evidence of the actual
                # method section. Prefer pages after the table of contents.
                evidence={"pdfPageOneBased":page_ix+1,"term":phrase,
                  "sourceExcerpt":" ".join(text[max(loc-85,0):min(end+110,len(text))].split())[:MAX_EXCERPT],
                  "indexOrIntroPagePossibility":page_ix<6}
                found[category].append(evidence)
        for idx,outcome in enumerate(registry_outcomes):
            if exact[idx]:continue
            measure=outcome["measure"]
            if not isinstance(measure,str) or not 12<=len(measure)<=600:
                continue
            needle=clean(measure)
            if needle in lower:
                exact[idx].append({"pdfPageOneBased":page_ix+1,
                       "match":"LITERAL_CURRENT_REGISTRY_MEASURE_TEXT_ON_PDF_PAGE"})
    return {
      "pageCount":len(doc),"searchableTextPages":searchable,
      "pagesInspected":min(len(doc),MAX_REVIEW_PAGES),
      "partialPdfReview":len(doc)>MAX_REVIEW_PAGES,
      "eightSourceReviewDomains":{
        category:{
          "sourceState":"PAGE_LINKED_TERMS_FOUND_REVIEW_REQUIRED" if hits
              else "NO_EXACT_TERMS_FOUND_NOT_PROOF_OF_ABSENCE",
          "pageLinkedSourceLeads":hits
        } for category,hits in found.items()
      },
      "currentRegisteredPrimaryEndpointLiteralMatches":[
        {"currentRegistryMeasure":entry["measure"],
         "currentRegistryTimeFrame":entry["timeFrame"],
         "sourceStatus":"LITERAL_MEASURE_TEXT_FOUND" if hits
              else "NO_LITERAL_MEASURE_TEXT_MATCH_NOT_PROOF_OF_ENDPOINT_CHANGE",
         "pdfPageLeads":hits} for entry,hits in zip(registry_outcomes,exact)
      ],
      "clinicalMethodCompletenessVerified":False,
      "historicalProspectiveSAPLockVerified":False,
      "statisticalReviewerSigned":False,
      "FDAOutcomeForecast":"ABSTAIN"
    }

def build(manifest:dict,source:dict,pdf_dir:Path,registry_dir:Path)->dict:
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        len(manifest.get("trialRows",[]))!=29 or len(manifest.get("applicationGroups",[]))!=23 or
        source.get("schema")!="MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH" or
        source.get("nctRosterCount")!=29 or source.get("applicationGroupCount")!=23 or
        source.get("currentRegistryDocumentEntries")!=23 or
        source.get("originalPdfBodiesRetrieved")!=23 or
        source.get("trialNctsWithDocumentEntries")!=12 or
        source.get("independentScientificGrades")!=0 or
        source.get("validatedFDAForecasts")!=0 or
        source.get("clinicalOrProductionWrites") is not False):
        raise ValueError("R53_IMMUTABLE_COMPLETE_RESEARCH_SOURCE_29_23_REQUIRED")
    if any(not path.is_dir() or path.is_symlink() for path in (pdf_dir,registry_dir)):
        raise ValueError("ORIGINAL_PUBLIC_PDF_AND_REGISTRY_ARCHIVES_REQUIRED")
    exact_ids={r["nct"] for r in manifest["trialRows"]}
    if len(exact_ids)!=29:raise ValueError("DUPLICATE_29_TRIAL_IDS")
    app_by_nct={n:[] for n in exact_ids}
    for app in manifest["applicationGroups"]:
        for nct in app["ncts"]:
            if nct not in app_by_nct or app["cycleId"] in app_by_nct[nct]:
                raise ValueError("ORIGINAL_APPLICATION_NCT_CROSSWALK_MISMATCH")
            app_by_nct[nct].append(app["cycleId"])
    entries=source.get("documentResearch")
    if not isinstance(entries,list) or len(entries)!=23:
        raise ValueError("ORIGINAL_23_PDF_SOURCE_ROWS_REQUIRED")
    seen=set();docs_by_trial={n:[] for n in exact_ids};reg_by_trial={}
    for row in entries:
        nct=row.get("nct");filename=row.get("archivedPdfFilename")
        if (nct not in exact_ids or not isinstance(filename,str) or
            not NAME_RE.fullmatch(filename) or not filename.startswith(nct+"-") or
            row.get("retrievalStatus")!="FETCHED" or row.get("pdfResearch") is None or
            row.get("applicationCycleIds")!=app_by_nct[nct]):
            raise ValueError("UNTRUSTED_OR_INCOMPLETE_CURRENT_PDF_PROVENANCE")
        if filename in seen:raise ValueError("DUPLICATED_ORIGINAL_PDF_ARCHIVE_FILENAME")
        seen.add(filename)
        sha=row.get("sourceSha256")
        if not isinstance(sha,str) or not SHA_RE.fullmatch(sha):
            raise ValueError("MISSING_DOCUMENT_SHA256")
        path=pdf_dir/filename
        if (not path.is_file() or path.is_symlink() or
            not path.resolve().is_relative_to(pdf_dir.resolve()) or
            not 100<=path.stat().st_size<=MAX_PDF_BYTES):
            raise ValueError("ORIGINAL_PDF_SOURCE_BYTES_UNAVAILABLE")
        original=path.read_bytes()
        if len(original)!=row.get("sourceBytes") or hashlib.sha256(original).hexdigest()!=sha:
            raise ValueError("ORIGINAL_PUBLIC_PDF_HASH_MISMATCH")
        if nct not in reg_by_trial:
            rp=registry_dir/(nct+".json")
            if not rp.is_file() or rp.is_symlink() or rp.stat().st_size>10_000_000:
                raise ValueError("ORIGINAL_REGISTRY_SOURCE_BYTES_MISSING")
            registry=json.loads(rp.read_bytes())
            if (registry.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct):
                raise ValueError("ORIGINAL_REGISTRY_NCT_MISMATCH")
            outcomes=(registry["protocolSection"].get("outcomesModule") or {}).get("primaryOutcomes") or []
            if (not isinstance(outcomes,list) or len(outcomes)>100 or
                any(not isinstance(o,dict) or not isinstance(o.get("measure"),str) or
                    not isinstance(o.get("timeFrame",""),str) for o in outcomes)):
                raise ValueError("UNVERIFIED_CURRENT_REGISTERED_ENDPOINTS")
            reg_by_trial[nct]={
              "sourceSha256":hashlib.sha256(rp.read_bytes()).hexdigest(),
              "currentPrimaryOutcomes":[{"measure":o["measure"],
                    "timeFrame":o.get("timeFrame","")} for o in outcomes]
            }
        evidence=inspect(original,nct,reg_by_trial[nct]["currentPrimaryOutcomes"])
        if evidence["pageCount"]!=row["pdfResearch"]["pageCount"]:
            raise ValueError("PDF_PAGE_COUNT_CHANGED_VERSUS_R53_SOURCE")
        docs_by_trial[nct].append({
           "filename":row["filename"],"sourceUrl":row["sourceUrl"],
           "sourceSha256":sha,"currentRegistryDocumentDateAsReported":row.get("currentRegistryDocumentDate"),
           "protocolFlagFromCurrentRegistry":row["hasProtocolFlag"],
           "sapFlagFromCurrentRegistry":row["hasSapFlag"],
           "machineTextEvidence":evidence,
           "originalDateSignedAndFirstPostedVerified":False,
           "regulatorOutcomePrediction":"ABSTAIN"
        })
    if len(seen)!=23 or sum(bool(d) for d in docs_by_trial.values())!=12:
        raise ValueError("ORIGINAL_ATTACHED_DOCUMENT_COVERAGE_CHANGED")
    trials=[]
    for nct in sorted(exact_ids):
        docs=sorted(docs_by_trial[nct],key=lambda x:x["filename"])
        sap_dates=[d["currentRegistryDocumentDateAsReported"] for d in docs if d["sapFlagFromCurrentRegistry"] and d["currentRegistryDocumentDateAsReported"]]
        protocol_dates=[d["currentRegistryDocumentDateAsReported"] for d in docs if d["protocolFlagFromCurrentRegistry"] and d["currentRegistryDocumentDateAsReported"]]
        flags=["HISTORICAL_FIRST_PUBLIC_SAP_DATE_NOT_VERIFIED",
               "ORIGINAL_PRE_UNBLINDING_SAP_LOCK_NOT_VERIFIED"]
        if not docs:flags.append("NO_CURRENT_REGISTRY_ATTACHED_PROTOCOL_SAP_OTHER_SOURCES_POSSIBLE")
        if sap_dates and protocol_dates:
            if max(sap_dates)<max(protocol_dates):
                flags.append("CURRENT_SAP_DOCUMENT_DATE_EARLIER_THAN_LATEST_ATTACHED_PROTOCOL_DATE_AMENDMENT_REVIEW")
            elif max(sap_dates)>max(protocol_dates):
                flags.append("CURRENT_SAP_DOCUMENT_DATE_LATER_THAN_LATEST_ATTACHED_PROTOCOL_DATE_VERSION_REVIEW")
        if len(docs)==1 and docs[0]["sapFlagFromCurrentRegistry"] and docs[0]["protocolFlagFromCurrentRegistry"]:
            flags.append("COMBINED_DOCUMENT_MAY_CONTAIN_ORIGINAL_AND_FINAL_VERSIONS_REVIEW_REQUIRED")
        trial={
            "nct":nct,"applicationCycleIds":sorted(app_by_nct[nct]),
            "currentRegistryPrimaryOutcomes":reg_by_trial.get(nct,{}).get("currentPrimaryOutcomes"),
            "currentRegistrySourceSha256":reg_by_trial.get(nct,{}).get("sourceSha256"),
            "sourceDocumentCount":len(docs),"documents":docs,
            "reviewFlags":flags,
            "scienceDimensions":len(DOMAINS),
            "originalPreReadoutVersionCrosswalkVerified":False,
            "independentStatisticalReviewComplete":False,
            "verifiedFDAForecast":"ABSTAIN"}
        trials.append(trial)
    app_rows=[]
    index={t["nct"]:t for t in trials}
    for app in manifest["applicationGroups"]:
        linked=[index[n] for n in app["ncts"]]
        docs=[d for t in linked for d in t["documents"]]
        domain_counts={name:sum(
             d["machineTextEvidence"]["eightSourceReviewDomains"][name]["sourceState"]=="PAGE_LINKED_TERMS_FOUND_REVIEW_REQUIRED"
             for d in docs) for name in DOMAINS}
        app_rows.append({
           "applicationCycleId":app["cycleId"],"ticker":app["ticker"],
           "exactNcts":list(app["ncts"]),
           "trialCount":len(linked),"availableCurrentPdfDocuments":len(docs),
           "protocolPDFAvailable":any(d["protocolFlagFromCurrentRegistry"] for d in docs),
           "sapPDFAvailable":any(d["sapFlagFromCurrentRegistry"] for d in docs),
           "eightScientificSourceReviewDimensions":domain_counts,
           "currentSourceMethodsPendingIndependentReview":True,
           "crossTrialDuplicationHandledWithUniqueNctIds":True,
           "originalPrimaryHierarchyVerified":False,
           "safetyCausalityVerified":False,
           "clinicalGrade":None,"fdaApprovalProbability":None,"officialFDAPrediction":"ABSTAIN"
        })
    return {
      "schema":"MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "canonicalTrials":29,"applicationGroups":23,
      "eightMethodsReviewDomains":list(DOMAINS),
      "currentPdfDocumentsSourceVerified":23,
      "trialsWithCurrentSourcePdfDocuments":12,
      "trialsWithoutCurrentAttachedProtocolSap":17,
      "applicationMethodsReview":app_rows,"trialMethodsReview":trials,
      "machineReadEvidenceNotHumanScientificAssessment":True,
      "documentDatesNotFirstPublicDates":True,
      "historicalLockedSapVersionsIndependentlyVerified":0,
      "independentlySignedClinicalMethodGrades":0,
      "independentlyValidatedApplicationFdaPredictions":0,
      "independentHistoricalFDAOutcomeBacktests":0,
      "measuredFDAApprovalAccuracy":None,
      "modelTrainingAuthorized":False,
      "clinicalOrProductionWrites":False,
      "officialPendingFDAOutcomePrediction":"ABSTAIN",
      "caution":"Keyword hits and literal current-registry endpoint matches provide page references for a real reviewer, not an adjudicated trial success, efficacy p-value, clinical safety causation, original prespecification, regulator outcome, or a measured prediction accuracy."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r53-report",type=Path,required=True)
    p.add_argument("--pdf-dir",type=Path,required=True)
    p.add_argument("--registry-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if (args.output.exists() or args.output.is_symlink() or
        not args.output.parent.is_dir() or not args.r53_report.is_file() or
        args.r53_report.is_symlink() or args.r53_report.stat().st_size>10_000_000):
        raise ValueError("WRITE_ONCE_EXACT_ORIGINAL_REPORT_REQUIRED")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    report=build(manifest,json.loads(args.r53_report.read_bytes()),
                 args.pdf_dir,args.registry_dir)
    with args.output.open("xb") as f:
        f.write((json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n").encode())
    print(json.dumps({k:report[k] for k in (
        "canonicalTrials","applicationGroups","currentPdfDocumentsSourceVerified",
        "trialsWithCurrentSourcePdfDocuments","trialsWithoutCurrentAttachedProtocolSap",
        "historicalLockedSapVersionsIndependentlyVerified",
        "independentlyValidatedApplicationFdaPredictions"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
