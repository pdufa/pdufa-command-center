#!/usr/bin/env python3
"""MAIN R66: first phase-first research gate from the exact 29 original registry bodies.

This is a deterministic, source-reported registration census: not an independent
trial-phase review, FDA review-cycle verification, study result or FDA forecast.
A registry phase, COMPLETED status, primary completion date or enrollment count
does not prove a trial met efficacy endpoints or that an FDA application was
accepted. Original source snapshots are dated and never silently refreshed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.refresh_focus_public_sources_r40 import APPS, ROSTER, _read_json, build_manifest

R46_SHA="7e1681399ed242d0080d8517bbe62cfb931e88e1340295fdf9839affbc0d3f92"
R65_SHA="1238d5a0ed120cd47d05dec12486e59e2bf8dbd6e7b73b989372955db622127a"
SCHEMA="MAIN_R66_EXACT_ORIGINAL_29_TRIAL_PHASE_SOURCE_CENSUS"
NCT=re.compile(r"NCT[0-9]{8}\Z")
HEX=re.compile(r"[a-f0-9]{64}\Z")
STATUS={"COMPLETED","ACTIVE_NOT_RECRUITING","RECRUITING"}
PHASES={("PHASE3",),("PHASE2","PHASE3")}
REPORTED_ALLOCATION={"RANDOMIZED","NA"}
REGISTRATION_FIELD_STATUS="REGISTRY_REPORTED_NOT_INDEPENDENTLY_ADJUDICATED"

def ensure(condition,code):
    if not condition:
        raise ValueError(code)

def guarded_json(path,*,max_size=18_000_000):
    ensure(path.is_file() and not path.is_symlink() and
           50<path.stat().st_size<=max_size,"INPUT_SOURCE_FILE_UNSAFE")
    data=path.read_bytes()
    val=json.loads(data)
    ensure(type(val) is dict,"INPUT_MUST_BE_JSON_OBJECT")
    return val,hashlib.sha256(data).hexdigest()

def index(rows,key,ids,label):
    ensure(type(rows) is list and len(rows)==len(ids) and
           all(type(r) is dict and type(r.get(key)) is str for r in rows),
           "UNTRUSTED_"+label+"_INDEX")
    out={r[key]:r for r in rows}
    ensure(len(out)==len(ids) and set(out)==set(ids),
           "UNTRUSTED_"+label+"_IDENTITY_OR_MEMBERSHIP")
    return out

def date_field(status,name):
    value=status.get(name)
    if value is None:
        return {"date":None,"sourceDateType":None}
    ensure(type(value) is dict and type(value.get("date")) is str
           and len(value["date"])<=10,"MALFORMED_SOURCE_DATE_"+name)
    date=value["date"]
    ensure(re.fullmatch(r"20[0-9]{2}(-[0-9]{2}){0,2}",date) is not None,
           "INVALID_REGISTRY_DATE_FORMAT_"+name)
    kind=value.get("type")
    ensure(kind is None or kind in ("ACTUAL","ESTIMATED"),
           "UNSUPPORTED_REGISTRY_DATE_TYPE_"+name)
    return {"date":date,"sourceDateType":kind}

def build(manifest,r46,r65,originals:Path,*,hashes):
    ensure(type(manifest) is dict and type(r46) is dict and type(r65) is dict
           and hashes=={"r46":R46_SHA,"r65":R65_SHA},
           "RESEARCH_ORIGINAL_INPUTS_NOT_PINNED")
    ensure(manifest.get("trialCount")==29 and manifest.get("applicationCount")==23
           and r46.get("schema")=="MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX"
           and r46.get("nctCount")==29 and r46.get("applicationGroupCount")==23
           and r46.get("registryRecordsFetched")==29
           and r46.get("scientificGradesWritten")==0
           and r46.get("signedIndependentReviews")==0
           and r46.get("validatedApplicationFdaForecasts")==0
           and r46.get("productionOrReviewerWrites") is False
           and r46.get("modelTrainingAuthorized") is False
           and r65.get("schema")=="MAIN_R65_ORIGINAL_SOURCE_HUMAN_ADJUDICATION_INTAKE_ONLY"
           and r65.get("exactNctCount")==29 and r65.get("provisionalApplicationCount")==23
           and r65.get("scientificReviewerTasks")==232
           and r65.get("originalMachinePdfPageLeads")==466
           and r65.get("qualifiedReviewerAttestationsRecorded")==0
           and r65.get("independentVerifiedPhaseEventsRecorded")==0
           and r65.get("independentlyCompletedMethodGrades")==0
           and r65.get("independentlyValidatedFDAApplicationPredictions")==0
           and r65.get("gradeOrProbabilityReleasePermitted") is False
           and r65.get("historicalOutcomeDataAccessed") is False
           and r65.get("reviewWritesEnabled") is False
           and r65.get("productionOrLedgerWrites") is False
           and r65.get("officialFDAOutcome")=="ABSTAIN"
           and r65.get("fdaReviewTiming")=="ABSTAIN"
           and r65.get("measuredOutOfTimeForecastAccuracy") is None,
           "UNRELEASED_SOURCE_ONLY_PHASE_INTAKE_REQUIRED")
    ensure(originals.is_dir() and not originals.is_symlink(),
           "IMMUTABLE_ORIGINAL_REGISTRY_DIRECTORY_MISSING")
    source_ids=[r["nct"] for r in manifest["trialRows"]]
    apps=manifest["applicationGroups"]
    app_ids=[a["cycleId"] for a in apps]
    ensure(len(set(source_ids))==29 and len(set(app_ids))==23,
           "DUPLICATED_ORIGINAL_FOCUS_SCOPE")
    receipt=index(r46.get("records"),"nct",source_ids,"R46")
    reviewer=index(r65.get("trialIndependentReviewPackets"),"nct",source_ids,"R65")
    expected_cycles={n:[] for n in source_ids}
    for app in apps:
        for n in app["ncts"]:
            ensure(n in expected_cycles and app["cycleId"] not in expected_cycles[n],
                   "APPLICATION_SOURCE_TRIAL_EDGE_INVALID")
            expected_cycles[n].append(app["cycleId"])
    cases=[]
    for n in source_ids:
        p=originals/(n+".json")
        ensure(p.is_file() and not p.is_symlink() and
               p.resolve().is_relative_to(originals.resolve()) and
               10<=p.stat().st_size<=10_000_000,
               "EXACT_ORIGINAL_JSON_RECORD_MISSING_"+n)
        raw=p.read_bytes()
        sha=hashlib.sha256(raw).hexdigest()
        receipt_row=receipt[n]
        review=reviewer[n]
        expected=sorted(expected_cycles[n])
        ensure(sha==receipt_row.get("sourceResponseSha256")==
               review.get("originalCurrentRegistrySha256")
               and len(raw)==receipt_row.get("sourceResponseBytes")
               and sorted(receipt_row.get("applicationCycleIds",[]))==expected
               and review.get("applicationCycleIds")==expected
               and review.get("mustVerifyTrialPhaseFirst") is True
               and review.get("phaseVerifiedByIndependentReviewer") is False
               and review.get("completedClinicalMethodScores")==0
               and review.get("clinicalAssessmentLevel")=="UNASSESSED_SOURCE_ONLY"
               and review.get("validatedFDAOutcome")=="ABSTAIN",
               "ORIGINAL_SHA_OR_PHASE_REVIEW_MEMBERSHIP_MISMATCH_"+n)
        study=json.loads(raw)
        proto=study.get("protocolSection")
        ensure(type(proto) is dict,"ORIGINAL_PROTOCOL_SECTION_MISSING_"+n)
        identity=proto.get("identificationModule",{})
        design=proto.get("designModule",{})
        status=proto.get("statusModule",{})
        conditions=proto.get("conditionsModule",{})
        interventions=proto.get("armsInterventionsModule",{})
        ensure(identity.get("nctId")==n and type(design) is dict and
               type(status) is dict and type(conditions) is dict and
               type(interventions) is dict,"PHASE_STUDY_SOURCE_IDENTITY_INVALID_"+n)
        phases=design.get("phases")
        ensure(design.get("studyType")=="INTERVENTIONAL"
               and type(phases) is list
               and tuple(phases) in PHASES
               and status.get("overallStatus") in STATUS,
               "UNEXPECTED_ORIGINAL_PHASE_OR_STATUS_"+n)
        design_info=design.get("designInfo") or {}
        allocation=design_info.get("allocation")
        enrollment=design.get("enrollmentInfo") or {}
        ensure(all(type(x) is dict for x in (design_info,enrollment))
               and allocation in REPORTED_ALLOCATION
               and type(enrollment.get("count")) is int
               and 0<enrollment["count"]<=100_000
               and enrollment.get("type") in ("ACTUAL","ESTIMATED"),
               "MALFORMED_ORIGINAL_STUDY_DESIGN_"+n)
        intervention_rows=interventions.get("interventions") or []
        condition_rows=conditions.get("conditions") or []
        ensure(type(intervention_rows) is list and 1<=len(intervention_rows)<=80
               and type(condition_rows) is list and 1<=len(condition_rows)<=100
               and all(type(i) is dict and type(i.get("name")) is str for i in intervention_rows)
               and all(type(c) is str for c in condition_rows),
               "UNTRUSTED_INTERVENTION_OR_CONDITION_SOURCE_"+n)
        last=date_field(status,"lastUpdatePostDateStruct")
        first=date_field(status,"studyFirstPostDateStruct")
        primary=date_field(status,"primaryCompletionDateStruct")
        completion=date_field(status,"completionDateStruct")
        verified=status.get("statusVerifiedDate")
        ensure(type(verified) is str and re.fullmatch(r"20\d{2}-\d{2}",verified),
               "REGISTRY_STATUS_VERIFICATION_MONTH_INVALID_"+n)
        ensure(type(last["date"]) is str and last["date"][:7]>=verified
               and type(first["date"]) is str and first["date"]<=last["date"],
               "REGISTRY_STATUS_REPORTING_DATE_CONFLICT_"+n)
        masking=(design_info.get("maskingInfo") or {}).get("masking")
        ensure(masking is None or type(masking) is str,"UNTRUSTED_MASKING_SOURCE_"+n)
        flags=[
          "PHASE_SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
          "REGISTRY_STATUS_NOT_FDA_APPLICATION_OUTCOME",
          "ORIGINAL_LOCKED_PHASE3_SAP_AND_PRIMARY_HIERARCHY_UNVERIFIED",
        ]
        if len(phases)!=1:flags.append("COMBINED_PHASE2_PHASE3_REVIEW_STUDY_DESIGN")
        if allocation!="RANDOMIZED":
            flags.append("NON_RANDOMIZED_ALLOCATION_LABEL_NEEDS_DESIGN_REVIEW")
        if status["overallStatus"]!="COMPLETED":
            flags.append("TRIAL_REGISTRY_STILL_IN_PROGRESS_NOT_APPROVAL_STATUS")
        cases.append({
          "nct":n,
          "applicationCycleIds":expected,
          "sourceOriginalResponseSha256":sha,
          "exactOriginalRegistryRecord":"https://clinicaltrials.gov/study/"+n,
          "sourceRegistryLastUpdatePostedDate":last["date"],
          "sourceReportedStatusVerifiedMonth":verified,
          "sourceReportedStudyType":design["studyType"],
          "sourceReportedPhases":list(phases),
          "sourceReportedStatus":status["overallStatus"],
          "sourceReportedAllocation":allocation,
          "sourceReportedMasking":masking,
          "sourceReportedEnrollmentCount":enrollment["count"],
          "sourceReportedEnrollmentType":enrollment["type"],
          "sourceReportedPrimaryCompletionDate":primary["date"],
          "sourceReportedPrimaryCompletionDateType":primary["sourceDateType"],
          "sourceReportedStudyCompletionDate":completion["date"],
          "sourceReportedStudyCompletionDateType":completion["sourceDateType"],
          "sourceConditionLabels":list(condition_rows),
          "sourceInterventionNames":[i["name"] for i in intervention_rows],
          "registrationVersusFDAReviewNotInterchangeable":True,
          "requiresHumanPhaseValidation":True,
          "independentPhaseReviewEventId":None,
          "originalPreUnblindingScientificHierarchyVerified":False,
          "clinicalMethodGradesCalculated":0,
          "fdaPrediction":"ABSTAIN",
          "phaseReviewFlags":flags
        })
    phase_count=Counter(tuple(x["sourceReportedPhases"]) for x in cases)
    status_count=Counter(x["sourceReportedStatus"] for x in cases)
    alloc_count=Counter(x["sourceReportedAllocation"] for x in cases)
    ensure(phase_count=={("PHASE3",):28,("PHASE2","PHASE3"):1}
           and status_count=={"COMPLETED":19,"ACTIVE_NOT_RECRUITING":8,"RECRUITING":2}
           and alloc_count=={"RANDOMIZED":28,"NA":1},
           "ORIGINAL_R53_PHASE_STATUS_CENSUS_DRIFT")
    grouped=[]
    by_trial={x["nct"]:x for x in cases}
    for app in apps:
        trial_refs=[by_trial[n] for n in app["ncts"]]
        grouped.append({
          "applicationCycleId":app["cycleId"],
          "ticker":app["ticker"],
          "linkedNcts":list(app["ncts"]),
          "reportedPhasesByExactTrial":[{
            "nct":x["nct"],"phases":x["sourceReportedPhases"],
            "registryStatus":x["sourceReportedStatus"],
            "statusSourceDate":x["sourceRegistryLastUpdatePostedDate"]
          } for x in trial_refs],
          "FDAApplicationStageConfirmedByThisRegistryCensus":False,
          "officialFDAOutcome":"ABSTAIN"
        })
    return {
      "schema":SCHEMA,
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "inputsPinnedOriginalSha256":dict(hashes),
      "exactNcts":29,"provisionalApplicationCycles":23,
      "registryReportedPhase3Only":28,
      "registryReportedPhase2Phase3":1,
      "registryReportedCompleted":19,
      "registryReportedActiveNotRecruiting":8,
      "registryReportedRecruiting":2,
      "registryReportedRandomized":28,
      "registryReportedAllocationNA":1,
      "registryReportedPhaseEvidenceCount":29,
      "independentlyQualifiedPhaseReviews":0,
      "signedScientificMethodGrades":0,
      "futureFDAOutcomePredictionsValidated":0,
      "measuredForecastAccuracy":None,
      "officialFutureFDAOutcome":"ABSTAIN",
      "officialFDAReviewDelay":"ABSTAIN",
      "productionOrReviewerLedgerWrites":False,
      "historicalOutcomesInspected":False,
      "phaseFieldsFromSourceAreNotClinicalOrRegulatoryAdjudications":True,
      "originalRegistryPhaseEvidence":cases,
      "provisionalApplicationPhaseEvidence":grouped
    }

def summary(d):
    lines=[
      "# MAIN R66: original source-reported phase census, 29 FOCUS trials",
      "",
      "The study phase and recruitment status are **registry-reported** as of each source record's dated last-update. ",
      "A source phase is not an independent phase verification or FDA acceptance decision.",
      "",
      "| Registry-reported category | Unique NCT count |",
      "| --- | ---: |",
      f'| Phase 3 only | {d["registryReportedPhase3Only"]} |',
      f'| Combined Phase 2/3 | {d["registryReportedPhase2Phase3"]} |',
      f'| Completed | {d["registryReportedCompleted"]} |',
      f'| Active, not recruiting | {d["registryReportedActiveNotRecruiting"]} |',
      f'| Recruiting | {d["registryReportedRecruiting"]} |',
      f'| Randomized | {d["registryReportedRandomized"]} |',
      f'| Allocation N/A | {d["registryReportedAllocationNA"]} |',
      "",
      "| NCT | Registry phase | Registry status | Registry last update | Source review flags |",
      "| --- | --- | --- | --- | --- |"
    ]
    for r in d["originalRegistryPhaseEvidence"]:
        lines.append(
          f'| [`{r["nct"]}`]({r["exactOriginalRegistryRecord"]})'
          f' | {", ".join(r["sourceReportedPhases"])}'
          f' | {r["sourceReportedStatus"]}'
          f' | {r["sourceRegistryLastUpdatePostedDate"]}'
          f' | {", ".join(r["phaseReviewFlags"])} |'
        )
    lines.extend([
      "", "**0 qualified phase reviewers, 0 method grades, 0 validated FDA forecasts, 0 backtests.**",
      "All future FDA outcome and timing predictions remain **ABSTAIN**.",
      "Source-reported completed status, phase, or randomization does not prove treatment efficacy or FDA application approval.",
      ""
    ])
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r46",required=True,type=Path)
    p.add_argument("--r65",required=True,type=Path)
    p.add_argument("--original-registry-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--summary",required=True,type=Path)
    args=p.parse_args()
    ensure(args.output!=args.summary and all(not x.exists() and
           not x.is_symlink() and x.parent.is_dir()
           for x in (args.output,args.summary)),
           "R66_OUTPUTS_MUST_BE_WRITE_ONCE")
    r46,h46=guarded_json(args.r46)
    r65,h65=guarded_json(args.r65)
    d=build(build_manifest(_read_json(ROSTER),_read_json(APPS)),
            r46,r65,args.original_registry_dir,
            hashes={"r46":h46,"r65":h65})
    with args.output.open("xb") as f:
        f.write((json.dumps(d,sort_keys=True,indent=2)+"\n").encode())
    with args.summary.open("xb") as f:
        f.write(summary(d).encode())
    print(json.dumps({k:d[k] for k in (
      "exactNcts","provisionalApplicationCycles",
      "registryReportedPhase3Only","registryReportedPhase2Phase3",
      "registryReportedCompleted","registryReportedActiveNotRecruiting",
      "registryReportedRecruiting","independentlyQualifiedPhaseReviews",
      "futureFDAOutcomePredictionsValidated")},sort_keys=True))

if __name__=="__main__":
    main()
