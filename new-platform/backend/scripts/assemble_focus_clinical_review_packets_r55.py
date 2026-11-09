#!/usr/bin/env python3
"""MAIN R55: join posted primary stats + arm-level AE counts to R54 methods pages.

Only independently verified CURRENT source JSON and original SHA receipts are
used. Preserve literal registry p-values, estimates and CI bounds; no efficacy
p-value recalculation, no multiplicity adjustment inferred, no pooled AE risk,
no model training or FDA prediction without independent review.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest

NCT=re.compile(r"NCT\d{8}\Z")
SHA=re.compile(r"[0-9a-f]{64}\Z")

def _value(v):
    if v is None or isinstance(v,(str,int,float,bool)):
        if isinstance(v,str) and len(v)>1800:raise ValueError("OVERSIZED_POSTED_SOURCE_VALUE")
        return v
    raise ValueError("INVALID_REPORTED_CLINICAL_NUMBER_OR_STRING")

def _source_rows(raw:dict,nct:str):
    if (not isinstance(raw,dict) or
        raw.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct):
        raise ValueError("ORIGINAL_REGISTERED_TRIAL_SOURCE_ID_MISMATCH")
    proto=raw["protocolSection"]
    outcomes=(proto.get("outcomesModule") or {}).get("primaryOutcomes") or []
    if not isinstance(outcomes,list) or len(outcomes)>100:
        raise ValueError("REGISTERED_PRIMARY_OUTCOME_SOURCE_MALFORMED")
    current_titles=[(str(q.get("measure","")).casefold().strip(),
                     str(q.get("timeFrame","")).casefold().strip()) for q in outcomes]
    result=raw.get("resultsSection") or {}
    om=result.get("outcomeMeasuresModule") or {}
    posted=om.get("outcomeMeasures") or []
    if not isinstance(posted,list) or len(posted)>400:
        raise ValueError("POSTED_CLINICAL_OUTCOME_LIMIT_EXCEEDED")
    primary=[]
    for item in posted:
        if not isinstance(item,dict):raise ValueError("UNTRUSTED_POSTED_OUTCOME_RECORD")
        if item.get("type")!="PRIMARY":continue
        title=_value(item.get("title"))
        timeframe=_value(item.get("timeFrame"))
        groups=item.get("groups") or []
        analyses=item.get("analyses") or []
        if (not isinstance(title,str) or not isinstance(timeframe,str) or
            not isinstance(groups,list) or len(groups)>100 or
            not isinstance(analyses,list) or len(analyses)>100):
            raise ValueError("MALFORMED_POSTED_PRIMARY_ANALYSIS")
        group_ids={x.get("id") for x in groups if isinstance(x,dict)}
        if len(group_ids)!=len(groups):raise ValueError("DUPLICATE_POSTED_ANALYSIS_GROUP")
        comparisons=[]
        for a in analyses:
            if (not isinstance(a,dict) or
                not isinstance(a.get("groupIds",[]),list) or
                any(g not in group_ids for g in a.get("groupIds",[]))):
                raise ValueError("POSTED_PRIMARY_SOURCE_COMPARISON_GROUP_MISMATCH")
            comparisons.append({
              "groupIds":list(a.get("groupIds",[])),
              "reportedPValueLiteral":_value(a.get("pValue")),
              "reportedStatisticalMethod":_value(a.get("statisticalMethod")),
              "reportedEstimateType":_value(a.get("paramType")),
              "reportedEstimateLiteral":_value(a.get("paramValue")),
              "reportedConfidenceLevelLiteral":_value(a.get("ciPctValue")),
              "reportedLowerBoundLiteral":_value(a.get("ciLowerLimit")),
              "reportedUpperBoundLiteral":_value(a.get("ciUpperLimit")),
              "methodSourceComment":_value(a.get("statisticalComment")),
              "nominalOrAdjustedStatusIndependentlyVerified":False,
              "independentStatisticalRecalculationComplete":False,
              "validatedTreatmentEffectClaim":False
            })
        for group in groups:
            if not isinstance(group.get("title"),str) or not isinstance(group.get("id"),str):
                raise ValueError("POSTED_PRIMARY_GROUP_ID_INVALID")
        primary.append({
            "titleAsPosted":title,"timeFrameAsPosted":timeframe,
            "sameTitleAndTimeFrameAsCurrentRegistration":(
                (title.casefold().strip(),timeframe.casefold().strip()) in current_titles
            ),
            "reportedGroupNames":[{"id":g["id"],"title":g["title"]} for g in groups],
            "statisticalComparisons":comparisons,
            "sourceComparisonsNotPrespecificationProof":True,
            "reportedResultsNotFDAReviewOutcome":True
        })
    ae=result.get("adverseEventsModule") or {}
    groups=ae.get("eventGroups") or []
    serious=ae.get("seriousEvents") or []
    other=ae.get("otherEvents") or []
    if (not isinstance(groups,list) or len(groups)>100 or
        not isinstance(serious,list) or len(serious)>5000 or
        not isinstance(other,list) or len(other)>5000):
        raise ValueError("MALFORMED_POSTED_SAFETY_MODULE")
    arm=[]
    for g in groups:
        if not isinstance(g,dict):raise ValueError("INVALID_SAFETY_GROUP")
        arm.append({
            "groupId":_value(g.get("id")),"groupName":_value(g.get("title")),
            "seriousAffected":_value(g.get("seriousNumAffected")),
            "seriousAtRisk":_value(g.get("seriousNumAtRisk")),
            "deathsAffected":_value(g.get("deathsNumAffected")),
            "deathsAtRisk":_value(g.get("deathsNumAtRisk")),
            "otherAffected":_value(g.get("otherNumAffected")),
            "otherAtRisk":_value(g.get("otherNumAtRisk")),
            "noCrossArmCausalComparisonAuthorized":True
        })
    posted_date=(proto.get("statusModule") or {}).get("resultsFirstPostDateStruct") or {}
    return {
        "postedPrimaryOutcomeTables":primary,
        "reportedPrimaryStatisticalComparisons":sum(len(x["statisticalComparisons"]) for x in primary),
        "postedAdverseEventArmCountsAsReported":arm,
        "seriousAeTermRowCount":len(serious),
        "otherAeTermRowCount":len(other),
        "resultsFirstPostedDateFromCurrentRecord":posted_date.get("date"),
        "currentRegisteredPrimaryEndpointCount":len(outcomes),
        "historicalOriginalRegisteredHierarchyUnverified":True,
        "trialResultsUnavailableInCurrentRegistryNotFailure":not bool(primary),
        "scientificBenefitRiskNotIndependentlyReviewed":True
    }

def assemble(manifest:dict,source_r46:dict,source_r54:dict,registry_dir:Path):
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        source_r46.get("schema")!="MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX" or
        source_r46.get("nctCount")!=29 or source_r46.get("applicationGroupCount")!=23 or
        source_r54.get("schema")!="MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX" or
        source_r54.get("canonicalTrials")!=29 or source_r54.get("applicationGroups")!=23 or
        source_r54.get("currentPdfDocumentsSourceVerified")!=23 or
        source_r54.get("independentlySignedClinicalMethodGrades")!=0 or
        source_r54.get("clinicalOrProductionWrites") is not False or
        not registry_dir.is_dir() or registry_dir.is_symlink()):
        raise ValueError("R54_AND_ORIGINAL_REGISTRY_29_23_IMMUTABLE_SOURCE_REQUIRED")
    index_r46={r["nct"]:r for r in source_r46.get("records",[])}
    index_r54={r["nct"]:r for r in source_r54.get("trialMethodsReview",[])}
    ids=[x["nct"] for x in manifest["trialRows"]]
    if (len(ids)!=29 or len(set(ids))!=29 or
        set(index_r46)!=set(ids) or len(source_r46["records"])!=29 or
        set(index_r54)!=set(ids) or len(source_r54["trialMethodsReview"])!=29 or
        len(source_r54.get("applicationMethodsReview",[]))!=23):
        raise ValueError("ORIGINAL_29_NCT_MEMBERSHIP_CHANGED")
    cross={n:[] for n in ids}
    for app in manifest["applicationGroups"]:
        for nct in app["ncts"]:
            if nct not in cross or app["cycleId"] in cross[nct]:
                raise ValueError("ORIGINAL_APPLICATION_TRIAL_IDENTITY_MISMATCH")
            cross[nct].append(app["cycleId"])
    records=[]
    for nct in ids:
        meta=index_r46[nct];methods=index_r54[nct]
        if (meta.get("applicationCycleIds")!=cross[nct] or
            methods.get("applicationCycleIds")!=sorted(cross[nct]) or
            methods.get("sourceDocumentCount")!=len(methods.get("documents",[]))):
            raise ValueError("SOURCE_GROUP_CROSSWALK_OR_DOCUMENT_COUNT_MISMATCH")
        path=registry_dir/(nct+".json")
        if (not path.is_file() or path.is_symlink() or
            not path.resolve().is_relative_to(registry_dir.resolve()) or
            path.stat().st_size>10_000_000):
            raise ValueError("ORIGINAL_PUBLIC_REGISTRY_RECORD_NOT_RETRIEVED")
        raw=path.read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        if sha!=meta.get("sourceResponseSha256") or len(raw)!=meta.get("sourceResponseBytes"):
            raise ValueError("ORIGINAL_REGISTRY_RECEIPT_MISMATCH")
        if methods.get("currentRegistrySourceSha256") not in (None,sha):
            raise ValueError("ORIGINAL_REGISTRY_DIFFERENT_FROM_R54_METHOD_VERSION")
        details=_source_rows(json.loads(raw),nct)
        records.append({
          "nct":nct,"applicationCycleIds":sorted(cross[nct]),
          "currentRegistrySourceSha256":sha,
          "currentRegistryOriginalUrl":"https://clinicaltrials.gov/study/"+nct,
          "sourceMethodsPageReferences":[
             {"filename":d["filename"],"sourceUrl":d["sourceUrl"],
              "sha256":d["sourceSha256"],
              "eightScientificMethodPageLeads":{
                 key:[v["pdfPageOneBased"] for v in obj["pageLinkedSourceLeads"]]
                 for key,obj in d["machineTextEvidence"]["eightSourceReviewDomains"].items()
              }}
             for d in methods["documents"]
          ],
          "methodsChronologyReviewFlags":methods["reviewFlags"],
          **details,
          "independentReviewerSigned":False,
          "scientificScore":None,
          "officialFDAOutcomeForecast":"ABSTAIN"
        })
    by_nct={r["nct"]:r for r in records}
    cases=[]
    for app in manifest["applicationGroups"]:
        evidence=[by_nct[n] for n in app["ncts"]]
        cases.append({
         "applicationCycleId":app["cycleId"],
         "ticker":app["ticker"],
         "drug":app["drug"],
         "indication":app["indication"],
         "reportedApplicationStageFromSnapshot":app["stage"],
         "exactNcts":list(app["ncts"]),
         "linkedTrialEvidence":[{"nct":n,"registrySourceSha256":by_nct[n]["currentRegistrySourceSha256"]}
             for n in app["ncts"]],
         "postedPrimaryTablesAcrossLinkedTrials":sum(len(t["postedPrimaryOutcomeTables"]) for t in evidence),
         "postedStatisticalComparisonsAcrossLinkedTrials":sum(t["reportedPrimaryStatisticalComparisons"] for t in evidence),
         "linkedTrialsWithCurrentAEArms":sum(bool(t["postedAdverseEventArmCountsAsReported"]) for t in evidence),
         "linkedTrialSafetyDenominatorsMustNotBePooled":True,
         "linkedCurrentProtocolSAPDocs":sum(len(t["sourceMethodsPageReferences"]) for t in evidence),
         "originalProspectiveStatisticalHierarchyIndependentlyVerified":False,
         "CMCAndFDAReviewDocumentationIndependentlyVerified":False,
         "independentClinicalReviewerSignoff":False,
         "scientificGrade":None,
         "fdaProbability":None,
         "officialFDAOutcomePrediction":"ABSTAIN",
         "officialDelayPrediction":"ABSTAIN",
         "nextReviewState":"SOURCE_POSTED_EFFICACY_SAFETY_AND_METHODS_REVIEW_NOT_SIGNED"
        })
    return {
      "schema":"MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nctTrials":29,"applicationGroups":23,
      "sourceVerifiedCurrentProtocolSAPDocuments":23,
      "uniqueTrialsWithPostedPrimary":sum(bool(r["postedPrimaryOutcomeTables"]) for r in records),
      "uniqueTrialsWithPostedAdverseEvents":sum(bool(r["postedAdverseEventArmCountsAsReported"]) for r in records),
      "postedPrimaryTables":sum(len(r["postedPrimaryOutcomeTables"]) for r in records),
      "reportedPrimaryStatisticalComparisons":sum(r["reportedPrimaryStatisticalComparisons"] for r in records),
      "seriousAeTermRows":sum(r["seriousAeTermRowCount"] for r in records),
      "otherAeTermRows":sum(r["otherAeTermRowCount"] for r in records),
      "currentSourceCasePackets":cases,
      "originalUniqueTrialEvidence":records,
      "currentPublicRegistryResultsAreNotOriginalPredecisionData":True,
      "reportedPValueNotIndependentlyMultiplicityAdjusted":True,
      "safetyArmsNotCausalOrPooled":True,
      "historicalLockedSAPsIndependentlyVerified":0,
      "signedScientificReviews":0,
      "independentlyValidatedFDAApplicationForecasts":0,
      "realHistoricalPredictionBacktests":0,
      "measuredAccuracy":None,
      "modelTrainingAuthorized":False,
      "clinicalOrProductionWrites":False,
      "officialPendingFDAOutcome":"ABSTAIN",
      "caution":"Original current registry JSON primary comparisons, arm-level AE counts and original public PDF method page leads are research evidence. No p-value verification against prospective SAP, no validated treatment benefit-risk, no CMC, no FDA forecast, no calibrated prediction."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r46-index",type=Path,required=True)
    p.add_argument("--r54-matrix",type=Path,required=True)
    p.add_argument("--registry-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if (a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir() or
        any(not q.is_file() or q.is_symlink() or q.stat().st_size>12_000_000
            for q in (a.r46_index,a.r54_matrix))):
        raise ValueError("R55_IMMUTABLE_INPUTS_AND_WRITE_ONCE_OUTPUT_REQUIRED")
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    d=assemble(m,json.loads(a.r46_index.read_bytes()),
               json.loads(a.r54_matrix.read_bytes()),a.registry_dir)
    with a.output.open("xb") as f:f.write((json.dumps(d,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:d[k] for k in (
        "nctTrials","applicationGroups","uniqueTrialsWithPostedPrimary",
        "uniqueTrialsWithPostedAdverseEvents","postedPrimaryTables",
        "reportedPrimaryStatisticalComparisons","seriousAeTermRows","otherAeTermRows",
        "signedScientificReviews","independentlyValidatedFDAApplicationForecasts"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
