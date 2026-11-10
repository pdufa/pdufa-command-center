#!/usr/bin/env python3
"""R47 track A: evidence-coverage checkpoint for the unchanged 29/23 FOCUS roster.

All three inputs are independently retrieved present-day public registry snapshots.
This is NOT the original pre-unblinding SAP, an efficacy model, or an FDA forecast.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER, APPS, _read_json, build_manifest
from scripts.research_workstream_history import digest

EXPECTED={
 "primary":("MAIN_R42_29_TRIAL_REGISTRY_PRIMARY_EVIDENCE","nctCount","applicationGroupCount"),
 "safety":("MAIN_R44_EXACT_NCT_POSTED_SAFETY_SOURCE_V1","nctCount","provisionalApplicationCount"),
 "documents":("MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX","nctCount","applicationGroupCount")
}
def canonical_manifest():
    return build_manifest(_read_json(ROSTER),_read_json(APPS))

def collect(inputs:dict[str,dict],source_hashes:dict[str,str],at:str,application_sources:dict|None=None)->dict:
    if set(inputs)!=set(EXPECTED) or set(source_hashes)!=set(EXPECTED):
        raise ValueError("THREE_INDEPENDENT_LIVE_SOURCE_FILES_REQUIRED")
    manifest=canonical_manifest()
    canonical={r["nct"] for r in manifest["trialRows"]}
    crosswalk={n:sorted(g["cycleId"] for g in manifest["applicationGroups"] if n in g["ncts"]) for n in canonical}
    maps={}
    for typ,(schema,nct_key,app_key) in EXPECTED.items():
        doc=inputs[typ]
        if not isinstance(doc,dict) or doc.get("schema")!=schema or doc.get(nct_key)!=29 or doc.get(app_key)!=23:
            raise ValueError("ORIGINAL_29_23_MEMBERSHIP_OR_SCHEMA_MISMATCH")
        rows=doc.get("records")
        if not isinstance(rows,list) or len(rows)!=29 or any(not isinstance(r,dict) or not isinstance(r.get("nct"),str) for r in rows):
            raise ValueError("NOT_EXACT_NCT_ROSTER")
        indexed={r["nct"]:r for r in rows}
        if len(indexed)!=29 or any(len(n)!=11 or not n.startswith("NCT") or not n[3:].isdigit() for n in indexed):
            raise ValueError("NCT_IDENTITY_DUPLICATE_OR_INVALID")
        maps[typ]=indexed
    ids=set(maps["documents"])
    if ids!=canonical or ids!=set(maps["primary"]) or ids!=set(maps["safety"]):
        raise ValueError("DISAGREEING_FOCUS_ROSTERS")
    for name,value in source_hashes.items():
        if not isinstance(value,str) or len(value)!=64 or any(x not in "0123456789abcdef" for x in value):
            raise ValueError("MISSING_SHA256_SOURCE_PROVENANCE")
    rows=[]
    for nct in sorted(ids):
        p,s,d=(maps[t][nct] for t in ("primary","safety","documents"))
        ids_app=d.get("applicationCycleIds")
        if (not isinstance(ids_app,list) or sorted(ids_app)!=crosswalk[nct] or
            (s.get("applicationCycleIds") is not None and sorted(s["applicationCycleIds"])!=crosswalk[nct])):
            raise ValueError("MISSING_APP_CROSSWALK")
        p_count=p.get("postedPrimaryOutcomeTableCount",0)
        ae_count=s.get("seriousEventTermCount",0)
        doc_count=d.get("currentAttachedDocumentCount",0)
        if any(type(x) is not int or x<0 for x in [p_count,ae_count,doc_count]):
            raise ValueError("INVALID_SOURCE_REVIEW_COUNTS")
        gaps=[]
        if p.get("sourceResponseSha256") is None:gaps.append("PRIMARY_REGISTRY_SOURCE_UNAVAILABLE")
        if s.get("sourceResponseSha256") is None:gaps.append("SAFETY_REGISTRY_SOURCE_UNAVAILABLE")
        if d.get("sourceResponseSha256") is None:gaps.append("DOCUMENT_REGISTRY_SOURCE_UNAVAILABLE")
        if not p_count:gaps.append("NO_POSTED_PRIMARY_RESULT_TABLE_IN_CURRENT_REGISTRY")
        if s.get("currentRegistryAdverseEventsModulePresent") is not True:gaps.append("NO_POSTED_SAFETY_MODULE_IN_CURRENT_REGISTRY")
        if d.get("currentSapAttachmentPresent") is not True:gaps.append("NO_CURRENT_REGISTRY_SAP_ATTACHMENT")
        gaps.extend(["PRE_READOUT_SAP_LOCK_NOT_INDEPENDENTLY_VERIFIED","ORIGINAL_FDA_REVIEW_CYCLE_NOT_INDEPENDENTLY_VERIFIED"])
        rows.append({
          "nct":nct,"applicationCycleIds":sorted(ids_app),
          "registrySourceUrl":"https://clinicaltrials.gov/study/"+nct,
          "sourceVersions":{kind:maps[kind][nct].get("sourceResponseSha256") for kind in EXPECTED},
          "currentRegistryPrimaryTables":p_count,"currentRegistrySaeTermEntries":ae_count,
          "currentRegistryAttachments":doc_count,
          "currentRegistrySapMetadataPresent":d.get("currentSapAttachmentPresent") is True,
          "missingEvidenceOrVerification":gaps,
          "independentlyVerifiedClinicalBenefitRisk":False,
          "originalPreReadoutSapLockedVerified":False,
          "regulatorFdaOutcomePrediction":"ABSTAIN",
          "numericalProbability":None
        })
    source_groups={}
    if application_sources is not None:
        if (application_sources.get("schema")!="MAIN_FOCUS_PUBLIC_SOURCE_RECAPTURE_R40" or
            application_sources.get("trialRoster")!=29 or application_sources.get("provisionalApplicationGroups")!=23 or
            application_sources.get("modelTrainingAuthorized") is not False or
            application_sources.get("noClinicalOrProductionWrites") is not True):
            raise ValueError("UNVERIFIED_APPLICATION_SOURCE_REFRESH")
        groups=application_sources.get("applicationGroups",[])
        source_groups={g["cycleId"]:g for g in groups}
        if len(groups)!=23 or set(source_groups)!={g["cycleId"] for g in manifest["applicationGroups"]}:
            raise ValueError("APPLICATION_REFRESH_CROSSWALK_MISMATCH")
    apps=[]
    for group in manifest["applicationGroups"]:
        cid=group["cycleId"];case_rows=[r for r in rows if cid in r["applicationCycleIds"]]
        refreshed=source_groups.get(cid)
        if refreshed is not None and sorted(refreshed.get("ncts",[]))!=sorted(group["ncts"]):
            raise ValueError("APPLICATION_REFRESH_TRIAL_IDENTITY_CHANGED")
        references=[]
        if refreshed:
            sources=[refreshed.get(key) for key in ("applicationSource","alternateOfficialSecSource")]
            sources.extend(refreshed.get("additionalOfficialFdaSources",[]))
            for source in sources:
                if source:
                    references.append({"url":source["url"],"retrievalStatus":source["status"],
                         "sha256":source.get("sha256"),"sourceRole":source.get("sourceRole","ISSUER_DISCLOSURE_NOT_INDEPENDENT_FDA_ACTION"),
                         "firstPublicVersionIndependentlyVerified":False})
        fingerprint={"trials":[{"nct":r["nct"],"sourceVersions":r["sourceVersions"]} for r in case_rows],
                     "applicationSources":references}
        apps.append({"applicationCycleId":cid,"ncts":sorted(group["ncts"]),
          "provisionalIndication":group["indication"],"applicationTypeFromSnapshot":group["applicationType"],
          "evidenceCutoffUtc":at,"evidenceFingerprint":digest(fingerprint),
          "sourceVersions":fingerprint,"applicationSourceReferences":references,
          "reasoning":"Current primary, safety and document sources are inventoried; independent benefit-risk, pre-readout SAP lock and exact FDA review-cycle verification remain required.",
          "counterevidenceAndGaps":sorted({gap for r in case_rows for gap in r["missingEvidenceOrVerification"]}),
          "uncertainty":"NOT_VALIDATED; document availability is not scientific or FDA reliability.",
          "scientificAssessmentStatus":"PHASE_APPROPRIATE_ORIGINAL_REVIEW_PENDING",
          "prediction":"NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT" if group["stage"]=="APPROVED_ALREADY" else "ABSTAIN",
          "reviewDelayPrediction":"NOT_APPLICABLE_ALREADY_OBSERVED_IN_SNAPSHOT" if group["stage"]=="APPROVED_ALREADY" else "ABSTAIN",
          "numericalProbability":None,"independentReviewerSigned":False,
          "existingUnsignedResearchLeansModified":False})
    return {
      "schema":"MAIN_R47_FOCUS_29_RESEARCH_CHECKPOINT",
      "applicationResearchRecords":apps,"newScientificallyQualifiedResearchPredictions":0,
      "sourceChangePolicy":"REOPEN_FOR_MATERIALITY_REVIEW_NOT_AUTOMATIC_GRADE_OR_PREDICTION",
      "canonicalRosterSha256":digest({"ncts":sorted(canonical),"crosswalk":crosswalk}),
      "generatedAtUtc":at,"exactNctCount":29,"provisionalApplicationCount":23,
      "sourceReceiptSha256":source_hashes,"rows":rows,
      "trialsWithCurrentPostedPrimaryTables":sum(r["currentRegistryPrimaryTables"]>0 for r in rows),
      "trialsWithCurrentRegistrySap":sum(r["currentRegistrySapMetadataPresent"] for r in rows),
      "trialsMissingAnyRequiredIndependentEvidence":sum(bool(r["missingEvidenceOrVerification"]) for r in rows),
      "independentlyVerifiedScientificGrades":0,"validatedFdaApplicationForecasts":0,
      "independentHistoricalBacktests":0,"calibratedAccuracy":None,
      "probabilityOrCertainty":None,"modelTrainingAuthorized":False,
      "automaticClinicalGradeWriteAuthorized":False,
      "productionWriteAuthorized":False,"officialFDAOutcomeForecast":"ABSTAIN",
      "status":"RESEARCH_EVIDENCE_GAP_ASSESSMENT_ONLY",
      "caution":"Sources show current registry evidence metadata only. This file is not an FDA prediction, original pre-readout SAP audit, or independent scientific review."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in EXPECTED:p.add_argument("--"+k,required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--application-sources",type=Path)
    args=p.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("WRITE_ONCE_RESEARCH_CHECKPOINT_REQUIRED")
    inputs={};hashes={}
    for k in EXPECTED:
        path=getattr(args,k)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>10_000_000:
            raise ValueError("MISSING_OR_UNSAFE_RESEARCH_FILE")
        buf=path.read_bytes()
        hashes[k]=hashlib.sha256(buf).hexdigest()
        inputs[k]=json.loads(buf)
    out=collect(inputs,hashes,datetime.now(timezone.utc).isoformat(timespec="seconds"),
      json.loads(args.application_sources.read_bytes()) if args.application_sources else None)
    with args.output.open("xb") as file:file.write((json.dumps(out,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:out[k] for k in ("exactNctCount","provisionalApplicationCount",
      "trialsWithCurrentPostedPrimaryTables","trialsWithCurrentRegistrySap",
      "trialsMissingAnyRequiredIndependentEvidence","validatedFdaApplicationForecasts",
      "status")},sort_keys=True))

if __name__=="__main__":main()
