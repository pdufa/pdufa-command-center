#!/usr/bin/env python3
"""R51: application-level SOURCE-REPORTED primary endpoint and safety evidence.

This is actual current ClinicalTrials.gov primary-outcome and adverse-event
content linked to all 23 original FOCUS application groups. Every parsed field
is re-extracted and checked against the archived original registry JSON; no
statistical significance, causal safety, original SAP lock or FDA decision is
adjudicated. All numerical values and p-values are quoted AS REPORTED.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import (
    ROSTER,APPS,_read_json,build_manifest
)
from scripts.build_focus_registry_results_r42 import extract as primary_extract
from scripts.build_focus_registry_safety_r44 import extract as safety_extract
from scripts.build_focus_protocol_index_r46 import extract as document_extract

SCHEMAS={
    "primary":("MAIN_R42_29_TRIAL_REGISTRY_PRIMARY_EVIDENCE","applicationGroupCount"),
    "safety":("MAIN_R44_EXACT_NCT_POSTED_SAFETY_SOURCE_V1","provisionalApplicationCount"),
    "documents":("MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX","applicationGroupCount")
}
SHA=re.compile("[a-f0-9]{64}\\Z")
def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def _normalize(value):
    return " ".join((value or "").casefold().split())

def _index(kind,source):
    schema,application_key=SCHEMAS[kind]
    if (not isinstance(source,dict) or source.get("schema")!=schema or
        source.get("nctCount")!=29 or source.get(application_key)!=23 or
        not isinstance(source.get("records"),list) or len(source["records"])!=29):
        raise ValueError("EXACT_FOCUS_29_23_SOURCE_SCHEMA_REQUIRED")
    index={r["nct"]:r for r in source["records"] if isinstance(r,dict) and
           isinstance(r.get("nct"),str)}
    if len(index)!=29:
        raise ValueError("DUPLICATE_OR_INVALID_REGISTRY_NCT")
    return index

def assess(manifest:dict,sources:dict[str,dict],raw_dir:Path)->dict:
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        len(manifest.get("trialRows",[]))!=29 or len(manifest.get("applicationGroups",[]))!=23):
        raise ValueError("CANONICAL_FOCUS_29_23_ROSTER_REQUIRED")
    if set(sources)!=set(SCHEMAS) or not raw_dir.is_dir() or raw_dir.is_symlink():
        raise ValueError("THREE_CURRENT_REGISTRY_SOURCES_AND_ARCHIVE_REQUIRED")
    ids=[row["nct"] for row in manifest["trialRows"]]
    if len(set(ids))!=29 or any(not re.fullmatch(r"NCT\d{8}",n) for n in ids):
        raise ValueError("ORIGINAL_NCT_MEMBERSHIP_CHANGED")
    apps={g["cycleId"]:g for g in manifest["applicationGroups"]}
    if len(apps)!=23:
        raise ValueError("APPLICATION_CYCLE_MEMBERSHIP_CHANGED")
    by_nct={n:[] for n in ids}
    for g in manifest["applicationGroups"]:
        if not isinstance(g.get("ncts"),list) or not g["ncts"]:
            raise ValueError("APPLICATION_MISSING_NCT")
        for n in g["ncts"]:
            if n not in by_nct or g["cycleId"] in by_nct[n]:
                raise ValueError("INVALID_OR_DUPLICATED_APPLICATION_TRIAL_LINK")
            by_nct[n].append(g["cycleId"])
    if any(not v for v in by_nct.values()):
        raise ValueError("UNASSIGNED_ORIGINAL_NCT")
    indexes={kind:_index(kind,d) for kind,d in sources.items()}
    if any(set(x)!=set(ids) for x in indexes.values()):
        raise ValueError("SOURCE_ROSTERS_NOT_IDENTICAL_TO_ORIGINAL_29")
    trial_rows=[]
    for nct in ids:
        p,s,d=(indexes[kind][nct] for kind in SCHEMAS)
        digests=[x.get("sourceResponseSha256") for x in (p,s,d)]
        if any(x is not None and (not isinstance(x,str) or not SHA.fullmatch(x))
               for x in digests):
            raise ValueError("INVALID_REGISTRY_SOURCE_SHA256")
        if s.get("applicationCycleIds",sorted(by_nct[nct]))!=by_nct[nct] or (
            d.get("applicationCycleIds",sorted(by_nct[nct]))!=by_nct[nct]):
            raise ValueError("MISMATCHED_ORIGINAL_APPLICATION_LINK")
        statuses=[x.get("sourceResponseSha256") is not None for x in (p,s,d)]
        # Never join results and AE modules fetched at different source versions.
        if not all(statuses):
            trial_rows.append({"nct":nct,"applicationCycleIds":sorted(by_nct[nct]),
                "evidenceStatus":"SOURCE_NOT_FULLY_RETRIEVED",
                "currentRegistrySourceSha256":None,
                "postedPrimaryOutcomeCount":0,"primary":[],
                "postedSafetyEventGroups":0,"eventGroups":[],
                "seriousEventTerms":[],"otherEventTerms":[],
                "primaryTitleTimeframeConcordance":[],
                "currentProtocolSapAttachments":[],
                "sourceGap":"NO_COMPARABLE_SINGLE_CURRENT_REGISTRY_SNAPSHOT",
                "clinicalBenefitRiskAdjudicated":False,"statisticalPlanVerified":False,
                "reviewerSigned":False,"forecast":"ABSTAIN"})
            continue
        if len(set(digests))!=1:
            raise ValueError("PRIMARY_SAFETY_DOCUMENTS_CAPTURED_DIFFERENT_SOURCE_VERSIONS")
        rawfile=raw_dir/(nct+".json")
        if (not rawfile.is_file() or rawfile.is_symlink() or
            not rawfile.resolve().is_relative_to(raw_dir.resolve()) or
            rawfile.stat().st_size>10_000_000):
            raise ValueError("ORIGINAL_RAW_REGISTRY_SOURCE_NOT_ARCHIVED")
        original=rawfile.read_bytes()
        if hashlib.sha256(original).hexdigest()!=digests[0]:
            raise ValueError("ORIGINAL_RAW_REGISTRY_SOURCE_SHA_MISMATCH")
        study=json.loads(original)
        rec={"url":p.get("sourceApiUrl"),"sha256":digests[0],"bytes":len(original)}
        if rec["url"]!="https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json":
            raise ValueError("NONORIGINAL_CLINICALTRIALS_API_URL")
        if any(x.get("sourceApiUrl")!=rec["url"] or x.get("sourceResponseBytes")!=len(original)
               for x in (p,s,d)):
            raise ValueError("REGISTRY_CAPTURE_PROVENANCE_INCONSISTENT")
        original_p=primary_extract(study,nct,rec)
        original_s=safety_extract(study,nct,rec,by_nct[nct])
        original_d=document_extract(study,nct,rec,by_nct[nct])
        if original_p!=p or original_s!=s or original_d!=d:
            raise ValueError("DERIVED_PRIMARY_SAFETY_OR_DOCUMENT_SOURCE_TAMPERED")
        protocol=study.get("protocolSection") or {}
        declarations=(protocol.get("outcomesModule") or {}).get("primaryOutcomes") or []
        if not isinstance(declarations,list) or len(declarations)>300:
            raise ValueError("MALFORMED_ORIGINAL_REGISTERED_PRIMARY_ENDPOINTS")
        registered=[{"titleAsCurrentlyRegistered":q.get("measure"),
                     "timeFrameAsCurrentlyRegistered":q.get("timeFrame"),
                     "descriptionAsCurrentlyRegistered":q.get("description")}
                    for q in declarations if isinstance(q,dict)]
        if len(registered)!=len(declarations) or len(registered)!=p["registeredPrimaryOutcomeCount"]:
            raise ValueError("REGISTERED_PRIMARY_ENDPOINT_COUNT_MISMATCH")
        concordance=[]
        for i,t in enumerate(p["primaryOutcomeTables"]):
            title=_normalize(t.get("title"))
            frame=_normalize(t.get("timeFrame"))
            matching=[j for j,reg in enumerate(registered)
                       if _normalize(reg["titleAsCurrentlyRegistered"])==title and
                          _normalize(reg["timeFrameAsCurrentlyRegistered"])==frame]
            known_group_ids={g.get("id") for g in t.get("groups",[])}
            if any(not set(a.get("groupIds",[])).issubset(known_group_ids)
                   for a in t.get("statisticalAnalyses",[])):
                raise ValueError("POSTED_ANALYSIS_GROUP_ID_NOT_IN_PRIMARY_TABLE")
            concordance.append({
                "postedPrimaryTableIndex":i,
                "currentRegisteredTitleAndTimeframeExactMatch":bool(matching),
                "currentRegisteredOutcomeIndices":matching,
                "historicalPreReadoutEndpointHierarchyVerified":False,
                "originalLockedSapMultiplicityVerified":False
            })
        if len(p["primaryOutcomeTables"])!=p["postedPrimaryOutcomeTableCount"]:
            raise ValueError("POSTED_PRIMARY_TABLE_COUNT_MISMATCH")
        if (len(s["eventGroups"])!=s["eventGroupCount"] or
            len(s["seriousEventTerms"])!=s["seriousEventTermCount"] or
            len(s["otherEventTerms"])!=s["otherEventTermCount"]):
            raise ValueError("POSTED_ADVERSE_EVENT_TERM_COUNT_MISMATCH")
        trial_rows.append({
          "nct":nct,"applicationCycleIds":sorted(by_nct[nct]),
          "evidenceStatus":"ORIGINAL_CURRENT_REGISTRY_RESULTS_EXTRACTED",
          "currentRegistrySourceUrl":"https://clinicaltrials.gov/study/"+nct,
          "currentRegistrySourceSha256":digests[0],
          "currentRegistryResultsFirstPostDateAsReported":p["postedResultsDateAsReported"],
          "currentRegistryLastUpdateAsReported":p["lastPostedUpdateAsReported"],
          "currentRegisteredPrimaryOutcomes":registered,
          "postedPrimaryOutcomeCount":len(p["primaryOutcomeTables"]),
          "primary":p["primaryOutcomeTables"],
          "primaryTitleTimeframeConcordance":concordance,
          "postedSafetyEventGroups":len(s["eventGroups"]),
          "eventGroups":s["eventGroups"],
          "seriousEventTerms":s["seriousEventTerms"],
          "otherEventTerms":s["otherEventTerms"],
          "safetyTimeFrameAsReported":s["timeFrameAsReported"],
          "currentProtocolSapAttachments":d["currentDocumentIndex"],
          "currentProtocolAttachmentPresent":d["currentProtocolAttachmentPresent"],
          "currentSapAttachmentPresent":d["currentSapAttachmentPresent"],
          "sourceGap":None,
          "clinicalBenefitRiskAdjudicated":False,
          "statisticalPlanVerified":False,
          "reviewerSigned":False,
          "forecast":"ABSTAIN"
        })
    indexed={r["nct"]:r for r in trial_rows}
    application_rows=[]
    for group in manifest["applicationGroups"]:
        ncts=group["ncts"]
        records=[indexed[n] for n in ncts]
        has_primary=any(r["postedPrimaryOutcomeCount"]>0 for r in records)
        has_safety=any(r["postedSafetyEventGroups"]>0 for r in records)
        has_sap=any(r.get("currentSapAttachmentPresent") is True for r in records)
        gaps=["ORIGINAL_PRE_READOUT_SAP_AND_MULTIPLICITY_NOT_VERIFIED",
              "FDA_APPLICATION_REVIEW_CYCLE_AND_CMC_NOT_INDEPENDENTLY_VERIFIED",
              "INDEPENDENT_BENEFIT_RISK_ASSESSMENT_NOT_SIGNED"]
        if not has_primary:gaps.append("NO_PRIMARY_TABLE_IN_CURRENT_REGISTRY_OTHER_PUBLIC_RESULTS_MAY_EXIST")
        if not has_safety:gaps.append("NO_AE_MODULE_IN_CURRENT_REGISTRY_OTHER_SAFETY_RESULTS_MAY_EXIST")
        if not has_sap:gaps.append("NO_CURRENT_REGISTRY_SAP_ATTACHMENT_OTHER_DOCUMENTS_MAY_EXIST")
        if any(r["evidenceStatus"]!="ORIGINAL_CURRENT_REGISTRY_RESULTS_EXTRACTED" for r in records):
            gaps.append("SOURCE_VERSION_UNAVAILABLE")
        if any(not x["currentRegisteredTitleAndTimeframeExactMatch"]
               for r in records for x in r["primaryTitleTimeframeConcordance"]):
            gaps.append("CURRENT_POSTED_PRIMARY_TITLE_TIMEFRAME_DOES_NOT_EXACTLY_MATCH_CURRENT_REGISTERED")
        application_rows.append({
            "applicationCycleId":group["cycleId"],
            "ticker":group.get("ticker"),"drug":group.get("drug"),"indication":group.get("indication"),
            "applicationTypeFromSnapshot":group.get("applicationType"),
            "applicationStageFromSnapshot":group.get("stage"),
            "exactNctIds":list(ncts),
            "currentPostedPrimaryTableCount":sum(r["postedPrimaryOutcomeCount"] for r in records),
            "currentReportedPrimaryStatisticalAnalysisCount":sum(
                 len(t["statisticalAnalyses"]) for r in records for t in r["primary"]),
            "currentReportedSeriousAeTermRowCount":sum(len(r["seriousEventTerms"]) for r in records),
            "currentReportedOtherAeTermRowCount":sum(len(r["otherEventTerms"]) for r in records),
            "currentRegistrySourceDigestsByNct":{n:indexed[n]["currentRegistrySourceSha256"] for n in ncts},
            "trialEvidenceReferences":[{"nct":n,"trialEvidenceRow":n} for n in ncts],
            "observedCurrentRegistryPrimaryTables":has_primary,
            "observedCurrentRegistryAdverseEvents":has_safety,
            "observedCurrentRegistrySapAttachments":has_sap,
            "criticalUnverifiedEvidence":gaps,
            "approvalOrCrlPrediction":"ABSTAIN" if group.get("stage")!="APPROVED_ALREADY"
               else "NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT",
            "reviewDelayPrediction":"ABSTAIN" if group.get("stage")!="APPROVED_ALREADY"
               else "NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT",
            "statisticalEfficacyConclusion":"NOT_INDEPENDENTLY_ADJUDICATED",
            "causalSafetyConclusion":"NOT_INDEPENDENTLY_ADJUDICATED",
            "numericalFdaProbability":None,"scientificGrade":None,
            "originalPreDecisionEvidenceAvailableVerified":False,
            "independentReviewerSignoff":False
        })
    return {
      "schema":"MAIN_R51_FOCUS_23_SOURCE_REPORTED_EFFICACY_AND_SAFETY_DOSSIERS",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "trialRosterCount":29,"applicationDossierCount":23,
      "uniqueTrialsWithCurrentPrimaryTables":sum(r["postedPrimaryOutcomeCount"]>0 for r in trial_rows),
      "uniqueTrialsWithCurrentAeModule":sum(r["postedSafetyEventGroups"]>0 for r in trial_rows),
      "currentPostedPrimaryTableCount":sum(r["postedPrimaryOutcomeCount"] for r in trial_rows),
      "currentReportedPrimaryStatisticalAnalysisCount":sum(
         len(t["statisticalAnalyses"]) for r in trial_rows for t in r["primary"]),
      "currentReportedSeriousAeTermRows":sum(len(r["seriousEventTerms"]) for r in trial_rows),
      "currentReportedOtherAeTermRows":sum(len(r["otherEventTerms"]) for r in trial_rows),
      "applicationsWithPostedPrimary":sum(a["observedCurrentRegistryPrimaryTables"] for a in application_rows),
      "applicationsWithPostedAeModule":sum(a["observedCurrentRegistryAdverseEvents"] for a in application_rows),
      "applicationDossiers":application_rows,"trialEvidence":trial_rows,
      "separateApplicationCyclesMayShareOneNct":True,
      "reportedPValuesAreNotMultiplicityValidated":True,
      "armSpecificSafetyNoPoolingOrCausality":True,
      "currentRegistryVersionNotOriginalPredecisionVersion":True,
      "unpostedIsNotTrialFailure":True,
      "independentScientificGrades":0,"validatedFDAForecasts":0,
      "historicalRealBacktests":0,"measuredApprovalAccuracy":None,
      "modelTrainingAuthorized":False,"productionOrClinicalLedgerWrites":False,
      "officialPendingFdaOutcomeAndTiming":"ABSTAIN",
      "note":"Source-reported current registry primary and AE data, not independently recalculated clinical efficacy, statistical significance, safety causality, FDA review, original prespecified SAP, CMC or clinical prediction."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in SCHEMAS:p.add_argument("--"+k,required=True,type=Path)
    p.add_argument("--original-raw-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("WRITE_ONCE_SOURCE_EVIDENCE_DOSSIER_REQUIRED")
    inputs={}
    for k in SCHEMAS:
        path=getattr(a,k)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>10_000_000:
            raise ValueError("UNTRUSTED_SOURCE_EVIDENCE_FILE")
        inputs[k]=json.loads(path.read_bytes())
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=assess(manifest,inputs,a.original_raw_dir)
    with a.output.open("xb") as f:
        f.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
       "trialRosterCount","applicationDossierCount",
       "uniqueTrialsWithCurrentPrimaryTables","uniqueTrialsWithCurrentAeModule",
       "currentPostedPrimaryTableCount","currentReportedPrimaryStatisticalAnalysisCount",
       "currentReportedSeriousAeTermRows","currentReportedOtherAeTermRows",
       "applicationsWithPostedPrimary","applicationsWithPostedAeModule",
       "independentScientificGrades","validatedFDAForecasts"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
