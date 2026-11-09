#!/usr/bin/env python3
"""MAIN R46: source-only original registry protocol/SAP attachment inventory.

File metadata in CURRENT ClinicalTrials.gov records does not verify a locked
pre-readout protocol/SAP, original first-publication date, or scientific merits.
No PDF body is retrieved or copied by this collector.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest,retrieve_url

NCT=re.compile(r"NCT[0-9]{8}\Z")
SAFE_FILENAME=re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,190}\.pdf\Z")

def trimmed(v,size=350):
    if isinstance(v,str): return v.strip()[:size] or None
    return None

def extract(study:dict,nct:str,receipt:dict,app_ids:list[str])->dict:
    if (not isinstance(study,dict) or not NCT.fullmatch(nct) or
        study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=nct):
        raise ValueError("SOURCE_NCT_IDENTITY_MISMATCH")
    if not isinstance(app_ids,list) or not app_ids:
        raise ValueError("MISSING_APPLICATION_CYCLE_CROSSWALK")
    status=study["protocolSection"].get("statusModule") or {}
    document_section=study.get("documentSection") or {}
    module=document_section.get("largeDocumentModule") or {}
    attachments=module.get("largeDocs") or []
    if not isinstance(attachments,list) or len(attachments)>100:
        raise ValueError("MALFORMED_ATTACHMENT_INDEX")
    result=[]
    seen=set()
    for item in attachments:
        if not isinstance(item,dict):raise ValueError("MALFORMED_ATTACHMENT_METADATA")
        filename=trimmed(item.get("filename"),190)
        if not filename or not SAFE_FILENAME.fullmatch(filename) or filename in seen:
            raise ValueError("UNSAFE_DUPLICATE_OR_INVALID_ATTACHMENT_NAME")
        seen.add(filename)
        kind=trimmed(item.get("typeAbbrev"),40)
        has_protocol=item.get("hasProtocol") is True
        has_sap=item.get("hasSap") is True
        date=trimmed(item.get("date"),40)
        if date and not re.fullmatch(r"20[0-9]{2}-[0-9]{2}-[0-9]{2}",date):
            raise ValueError("MALFORMED_ATTACHMENT_DOCUMENT_DATE")
        result.append({
          "typeAsRegistry":kind,
          "filenameAsRegistry":filename,
          "documentDateAsRegistry":date,
          "hasProtocolFlagAsRegistry":has_protocol,
          "hasSapFlagAsRegistry":has_sap,
          "documentDescriptionAsRegistry":trimmed(item.get("label"),400),
          "originalPdfBodyRetrieved":False,
          "documentDateVerifiedAsFirstPublic":False,
          "preReadoutLockedVersionVerified":False
        })
    first=status.get("studyFirstPostDateStruct") or {}
    last=status.get("lastUpdatePostDateStruct") or {}
    return {
      "nct":nct,"applicationCycleIds":list(app_ids),
      "originalRegistryUrl":"https://clinicaltrials.gov/study/"+nct,
      "sourceApiUrl":receipt.get("url"),
      "sourceResponseSha256":receipt.get("sha256"),
      "sourceResponseBytes":receipt.get("bytes"),
      "studyFirstPostedDateFromCurrentRecord":trimmed(first.get("date"),40),
      "registryLastUpdatePostedDateFromCurrentRecord":trimmed(last.get("date"),40),
      "currentAttachedDocumentCount":len(result),
      "currentProtocolAttachmentPresent":any(d["hasProtocolFlagAsRegistry"] for d in result),
      "currentSapAttachmentPresent":any(d["hasSapFlagAsRegistry"] for d in result),
      "currentDocumentIndex":result,
      "attachmentStatus":"CURRENT_ATTACHED_PROTOCOL_OR_SAP" if any(
         d["hasProtocolFlagAsRegistry"] or d["hasSapFlagAsRegistry"] for d in result
        ) else ("CURRENT_OTHER_ATTACHMENT_ONLY" if result else "NO_CURRENT_REGISTRY_ATTACHMENT"),
      "historicalRegistryAmendmentChainVerified":False,
      "lockedSapAndPrespecifiedMultiplicityVerified":False,
      "independentClinicalReview":False,
      "scientificMethodGrade":None,
      "officialFDAForecast":"ABSTAIN",
      "reviewDelayForecast":"ABSTAIN"
    }

def run(manifest:dict,fetcher=retrieve_url,raw_dir:Path|None=None)->dict:
    if (manifest.get("trialCount")!=29 or manifest.get("applicationCount")!=23 or
        len(manifest.get("trialRows",[]))!=29 or len(manifest.get("applicationGroups",[]))!=23):
        raise ValueError("EXACT_29_23_SOURCE_MANIFEST_REQUIRED")
    ids={item["nct"]:[] for item in manifest["trialRows"]}
    if len(ids)!=29:raise ValueError("DUPLICATED_NCT")
    for app in manifest["applicationGroups"]:
        for n in app["ncts"]:
            if n not in ids:raise ValueError("NCT_APPLICATION_MISMATCH")
            ids[n].append(app["cycleId"])
    if any(not v for v in ids.values()):raise ValueError("INCOMPLETE_APP_CROSSWALK")
    if raw_dir is not None and (not raw_dir.is_dir() or raw_dir.is_symlink()):
        raise ValueError("RAW_ARCHIVE_DIRECTORY_NOT_READY")
    def read(item):
        nct=item["nct"]
        response,raw=fetcher(item["registryUrl"])
        if response.get("status")!="FETCHED" or raw is None:
            return nct,{"nct":nct,"applicationCycleIds":ids[nct],
              "attachmentStatus":"REGISTRY_SOURCE_UNAVAILABLE","sourceStatus":response.get("status"),
              "scientificMethodGrade":None,"officialFDAForecast":"ABSTAIN"},None
        if hashlib.sha256(raw).hexdigest()!=response.get("sha256"):
            raise ValueError("ORIGINAL_REGISTRY_SHA256_MISMATCH")
        try:rec=extract(json.loads(raw),nct,response,ids[nct])
        except (KeyError,ValueError,TypeError):
            return nct,{"nct":nct,"applicationCycleIds":ids[nct],
              "attachmentStatus":"UNVERIFIED_REGISTRY_IDENTITY_OR_STRUCTURE",
              "scientificMethodGrade":None,"officialFDAForecast":"ABSTAIN"},None
        return nct,rec,raw
    indexed={}
    with ThreadPoolExecutor(max_workers=5) as pool:
        for future in as_completed([pool.submit(read,x) for x in manifest["trialRows"]]):
            nct,entry,raw=future.result()
            indexed[nct]=entry
            if raw is not None and raw_dir is not None:
                with (raw_dir/(nct+".json")).open("xb") as f:f.write(raw)
    entries=[indexed[x["nct"]] for x in manifest["trialRows"]]
    if len(entries)!=29 or len({x["nct"] for x in entries})!=29:
        raise ValueError("ROSTER_MEMBERSHIP_CHANGED")
    return {
      "schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
      "asOf":manifest["asOf"],
      "observedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nctCount":29,"applicationGroupCount":23,
      "registryRecordsFetched":sum(x.get("sourceResponseSha256") is not None for x in entries),
      "trialsWithCurrentAttachments":sum(x.get("currentAttachedDocumentCount",0)>0 for x in entries),
      "trialsWithCurrentProtocol":sum(x.get("currentProtocolAttachmentPresent") is True for x in entries),
      "trialsWithCurrentSap":sum(x.get("currentSapAttachmentPresent") is True for x in entries),
      "attachmentEntries":sum(x.get("currentAttachedDocumentCount",0) for x in entries),
      "missingCurrentAttachments":sum(x.get("attachmentStatus")=="NO_CURRENT_REGISTRY_ATTACHMENT" for x in entries),
      "records":entries,
      "preReadoutSapVersionsIndependentlyVerified":0,
      "scientificGradesWritten":0,
      "signedIndependentReviews":0,
      "validatedApplicationFdaForecasts":0,
      "historicalBacktests":0,
      "approvalProbability":None,"historicalAccuracy":None,
      "futureFdaForecast":"ABSTAIN","futureReviewDelayForecast":"ABSTAIN",
      "modelTrainingAuthorized":False,
      "productionOrReviewerWrites":False,
      "caution":"Current registry attachment metadata and its document date DO NOT establish the exact version publicly available at original Phase 3 readout, locked SAP, study endpoint multiplicity, manufacturing adequacy or a clinical prediction. Absence in current registry does not prove protocol/SAP unavailable elsewhere."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--raw-dir",required=True,type=Path)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("IMMUTABLE_OUTPUT_REQUIRED")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=run(manifest,raw_dir=args.raw_dir)
    with args.output.open("xb") as f:
        f.write((json.dumps(result,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
       "nctCount","applicationGroupCount","registryRecordsFetched",
       "trialsWithCurrentAttachments","trialsWithCurrentProtocol","trialsWithCurrentSap",
       "attachmentEntries","missingCurrentAttachments",
       "preReadoutSapVersionsIndependentlyVerified","validatedApplicationFdaForecasts")}),flush=True)

if __name__=="__main__":main()
