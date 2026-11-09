#!/usr/bin/env python3
"""MAIN R49: cross-check 412 selected FDA action leads with both ORIGINAL captured archive datasets.

An original-source record/ORIG submission match is not a verified FDA review
cycle, clinical trial source version, or unbiased historical prediction case.
FDA action labels live ONLY in a postdecision evidence audit, never forecaster inputs.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from collections import Counter
from datetime import date,datetime,timezone
from pathlib import Path
from scripts.build_historical_source_identity_audit_r48 import triage

SHA=re.compile(r"[a-f0-9]{64}\Z")
APP=re.compile(r"(?:NDA|BLA)[0-9]{6}\Z")
def _iso(raw,pattern):
    if not isinstance(raw,str) or not re.fullmatch(pattern,raw):
        raise ValueError("MALFORMED_OFFICIAL_SOURCE_ACTION_DATE")
    if len(raw)==8 and raw.isdigit():
        return datetime.strptime(raw,"%Y%m%d").date().isoformat()
    return datetime.strptime(raw,"%m/%d/%Y").date().isoformat()

def _source(source,kind):
    statuses={
      "approved":"APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
      "crl":"QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT"
    }
    if (not isinstance(source,dict) or source.get("schema_version")!=1 or
        source.get("status")!=statuses[kind] or
        not isinstance(source.get("records"),list) or not source["records"]):
        raise ValueError("UNTRUSTED_OFFICIAL_FDA_SOURCE_SNAPSHOT")
    field="record_sha256" if kind=="approved" else "source_record_sha256"
    result={}
    for r in source["records"]:
        digest=r.get(field) if isinstance(r,dict) else None
        if not isinstance(digest,str) or not SHA.fullmatch(digest) or digest in result:
            raise ValueError("DUPLICATED_OR_UNHASHED_FDA_ORIGINAL_RECORD")
        result[digest]=r
    return result

def crosscheck(rows,receipt,raw,approved,approved_raw,crl,crl_raw,identity,at):
    triage_result,_=triage(rows,receipt,raw,at)
    if (not isinstance(identity,dict) or
        identity.get("schema")!="MAIN_R48_SELECTED_FDA_SOURCE_PARENT_ACTION_AUDIT" or
        identity.get("originalFdaCandidateSha256")!=hashlib.sha256(raw).hexdigest() or
        identity.get("sourceActionRecords")!=len(rows) or
        identity.get("sourceIdentityGroups")!=triage_result["sourceIdentityGroups"] or
        identity.get("independentApplicationReviewCyclesVerified")!=0 or
        identity.get("modelTrainingAuthorized") is not False):
        raise ValueError("R48_PARENT_SOURCE_IDENTITY_AUDIT_REQUIRED")
    proven=receipt.get("sourceProvenance")
    if not isinstance(proven,dict):raise ValueError("MISSING_ORIGINAL_SOURCE_ARCHIVE_CHAIN")
    for k,original in [("approvedRegistry",approved_raw),("selectedCrl",crl_raw)]:
        v=proven.get(k)
        if (not isinstance(v,dict) or v.get("sha256")!=hashlib.sha256(original).hexdigest()
            or v.get("bytes")!=len(original) or not isinstance(v.get("retrievedOn"),str)):
            raise ValueError("OFFICIAL_ARCHIVE_SHA_OR_LENGTH_MISMATCH")
    # Parsed FDA source objects must match the immutable originally retrieved
    # source bytes. The source snapshot SHA receipts alone are insufficient if
    # caller-owned parsed objects can be replaced before reconciliation.
    try:
        if json.loads(approved_raw)!=approved or json.loads(crl_raw)!=crl:
            raise ValueError("FDA_PARSED_SOURCE_DIFFERS_FROM_IMMUTABLE_ARCHIVE_BYTES")
    except (TypeError,UnicodeDecodeError,json.JSONDecodeError):
        raise ValueError("UNPARSEABLE_ORIGINAL_FDA_ARCHIVE_BYTES")
    ap=_source(approved,"approved")
    cp=_source(crl,"crl")
    events=[];matched=Counter();issues=Counter()
    for row in rows:
        digest=row["sourceRecordSha256"]
        kind=row["source"]
        source=ap.get(digest) if kind=="DRUGSFDA_APPROVED_PRODUCT_REGISTRY" else (
            cp.get(digest) if kind=="OPENFDA_SELECTED_PUBLIC_CRL_LETTERS" else None)
        ok=False;reason=None
        detail={}
        if kind=="DRUGSFDA_APPROVED_PRODUCT_REGISTRY":
            if source is None:reason="ORIGINAL_APPROVAL_RECORD_SHA_NOT_FOUND"
            elif (row.get("applicationId")!=source.get("application_number_as_published") or
                  row.get("sourceAction") not in ("AP","TA") or
                  row.get("researchClass") not in ("AP_SOURCE_REGISTRY","TA_NONBINARY_SOURCE_REGISTRY")):
                reason="FDA_APPROVAL_PARENT_OR_ACTION_CLASS_MISMATCH"
            else:
                original=[]
                for submission in source.get("submissions_as_published",[]):
                    if (submission.get("submission_type_as_published")=="ORIG" and
                        submission.get("submission_number_as_published")==row.get("sourceOriginalSubmissionNo") and
                        submission.get("submission_status_as_published")==row["sourceAction"]):
                        original.append(submission)
                exact=[s for s in original if
                    _iso(s.get("submission_status_date_as_published"),r"\d{8}")==row["reportedActionDate"]]
                if len(exact)!=1:reason="ORIGINAL_SUBMISSION_DATE_NUMBER_NOT_UNIQUE_OR_MISMATCH"
                else:
                    ok=True;matched["approvedOriginal" if row["sourceAction"]=="AP" else "tentativeOriginal"]+=1
                    detail={"submissionTypeFromOriginal":"ORIG",
                      "submissionNumberFromOriginal":exact[0]["submission_number_as_published"],
                      "originalSourceRegistryRecordIndex":source.get("source_record_index"),
                      "originalSourceSponsorAsPublished":source.get("sponsor_name_as_published")}
        elif kind=="OPENFDA_SELECTED_PUBLIC_CRL_LETTERS":
            if source is None:reason="ORIGINAL_CRL_RECORD_SHA_NOT_FOUND"
            elif source.get("letter_type_as_published")!="COMPLETE RESPONSE" or row.get("sourceAction")!="COMPLETE RESPONSE":
                reason="ORIGINAL_CRL_LETTER_TYPE_MISMATCH"
            elif row.get("sourceApplicationReferences")!=source.get("application_numbers"):
                reason="ORIGINAL_CRL_APPLICATION_REFERENCE_MISMATCH"
            elif _iso(source.get("letter_date_as_published"),r"\d{2}/\d{2}/\d{4}")!=row.get("reportedActionDate"):
                reason="ORIGINAL_CRL_LETTER_DATE_MISMATCH"
            else:
                ok=True;matched["publishedCrlRecord"]+=1
                detail={"originalSourceFileNameAsPublished":source.get("file_name_as_published"),
                  "originalSourceIndex":source.get("source_record_index"),
                  "originalSourceCompanyAsPublished":source.get("company_name_as_published")}
                if row.get("researchClass")=="CRL_EXPLICIT_ORIGINAL":
                    ref="Original "+row.get("sourceOriginalOrSupplementUnit","")
                    if not any(ref in x for x in source["application_numbers"]):
                        ok=False;reason="EXPLICIT_ORIGINAL_UNIT_NOT_SUPPORTED_BY_SOURCE"
                    else:matched["crlReferenceWithExplicitOriginalUnit"]+=1
        else:reason="FDA_ACTION_SOURCE_CATEGORY_UNRECOGNIZED"
        if ok:matched["total"]+=1
        else:issues[reason]+=1
        events.append({
          "parentApplicationAsPublished":row.get("applicationId"),
          "sourceActionRecordSha256":digest,
          "sourceArchiveKind":kind,
          "reportedActionDateFromPostdecisionSource":row.get("reportedActionDate"),
          "publishedActionType":row["sourceAction"],
          "researchClass":row["researchClass"],
          "originalCapturedSourceRecordLinked":ok,
          "sourceLinkageProblem":reason,
          "originalSourceMetadata":detail,
          "independentFdaReviewCycleAdjudicated":False,
          "modelEligible":False,
          "predictionOrValidationAuthorized":False
        })
    result={
      "schema":"MAIN_R49_FDA_ORIGINAL_PUBLISHED_ACTION_SOURCE_CROSSCHECK",
      "asOfUtc":at,
      "sourceRecordRows":len(rows),
      "reconciledOriginalSourceActionRows":matched["total"],
      "unreconciledSourceActionRows":len(rows)-matched["total"],
      "reconciledOriginalApplicationApprovalRows":matched["approvedOriginal"],
      "reconciledOriginalApplicationTentativeApprovalRows":matched["tentativeOriginal"],
      "reconciledPublishedCrlRows":matched["publishedCrlRecord"],
      "publishedCrlWithExplicitOriginalSubmissionReference":matched["crlReferenceWithExplicitOriginalUnit"],
      "sourceLinkageProblems":dict(sorted(issues.items())),
      "originalSnapshotSha256":{
        "approvedProductRegistry":hashlib.sha256(approved_raw).hexdigest(),
        "selectedPublishedCrlRegistry":hashlib.sha256(crl_raw).hexdigest()
      },
      "sourceCandidateFileSha256":hashlib.sha256(raw).hexdigest(),
      "r48GroupedParentSourceIdentities":triage_result["sourceIdentityGroups"],
      "r48RepeatedParentIdGroups":triage_result["knownParentGroupsWithMultipleSourceRows"],
      "r48MixedApprovalAndCrlParentIdGroups":triage_result["knownParentGroupsWithMixedApprovalAndCrlSourceTypes"],
      "actionSideAuditRecords":events,
      "sourceSelectionOutcomeBiased":True,
      "consecutiveOriginalNdaBlaApplicationFilingRosterVerified":False,
      "completePublicCrlAndNonapprovalDenominatorVerified":False,
      "exactFdaDecisionCyclesIndependentlyAdjudicated":0,
      "predecisionEvidenceSnapshotsIndependentlyVerified":0,
      "independentRealHistoricalPredictions":0,
      "independentRetrospectiveBacktests":0,
      "measuredPredictiveAccuracy":None,"calibratedFdaProbability":None,
      "modelTrainingAuthorized":False,"productionMutationAuthorized":False,
      "officialFutureFdaForecast":"ABSTAIN",
      "warning":"These matches verify fields against two captured FDA public-source datasets. FDA original filing cycles, first publication of decision letters, clinical evidence as of the prediction cutoff, untouched validation and the full denominator remain UNVERIFIED. Event rows include postdecision outcomes and must never enter a forecaster."
    }
    if len(events)!=len(rows) or sum(issues.values())+matched["total"]!=len(rows):
        raise ValueError("SOURCE_RECONCILIATION_CARDINALITY_ERROR")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("candidates","receipt","approved","crl","identity","output"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("WRITE_ONCE_FDA_POSTDECISION_AUDIT_REQUIRED")
    original={}
    for name in ("candidates","receipt","approved","crl","identity"):
        path=getattr(a,name)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>85_000_000:
            raise ValueError("SOURCE_FILE_INVALID_OR_UNBOUNDED")
        original[name]=path.read_bytes()
    report=crosscheck(
      json.loads(original["candidates"]),json.loads(original["receipt"]),original["candidates"],
      json.loads(original["approved"]),original["approved"],
      json.loads(original["crl"]),original["crl"],
      json.loads(original["identity"]),
      datetime.now(timezone.utc).isoformat(timespec="seconds"))
    with a.output.open("xb") as f:f.write((json.dumps(report,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:report[k] for k in (
       "sourceRecordRows","reconciledOriginalSourceActionRows","unreconciledSourceActionRows",
       "reconciledOriginalApplicationApprovalRows","reconciledOriginalApplicationTentativeApprovalRows",
       "reconciledPublishedCrlRows","r48GroupedParentSourceIdentities",
       "exactFdaDecisionCyclesIndependentlyAdjudicated","independentRetrospectiveBacktests"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
