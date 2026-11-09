"""MAIN R49: verify source-side archived NDA/BLA action dates and hash provenance only."""
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_historical_source_identity_audit_r48 import triage
from scripts.crosscheck_historical_fda_action_sources_r49 import crosscheck

def fixture():
    approved_record={
       "application_number_as_published":"BLA761343",
       "record_sha256":"a"*64,
       "source_record_index":25,
       "sponsor_name_as_published":"Original Sponsor",
       "submissions_as_published":[
         {"submission_type_as_published":"ORIG","submission_number_as_published":"1",
          "submission_status_as_published":"AP","submission_status_date_as_published":"20240416"},
         {"submission_type_as_published":"SUPPL","submission_number_as_published":"1",
          "submission_status_as_published":"AP","submission_status_date_as_published":"20241018"}
       ]
    }
    crl_record={
      "source_record_sha256":"b"*64,
      "application_numbers":["BLA 761343/Original 1"],
      "letter_date_as_published":"10/11/2023",
      "letter_type_as_published":"COMPLETE RESPONSE",
      "file_name_as_published":"761343_2024_Orig1s000OtherActionLtrs.pdf",
      "company_name_as_published":"Original Sponsor","source_record_index":17
    }
    ap={
      "schema_version":1,"status":"APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
      "records":[approved_record]
    }
    crl={
      "schema_version":1,"status":"QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
      "records":[crl_record]
    }
    rows=[
      {"applicationId":"BLA761343","source":"DRUGSFDA_APPROVED_PRODUCT_REGISTRY",
       "sourceRecordSha256":"a"*64,"sourceAction":"AP",
       "reportedActionDate":"2024-04-16",
       "sourceOriginalSubmissionNo":"1",
       "researchClass":"AP_SOURCE_REGISTRY",
       "exactReviewCycleIndependentlyVerified":False,
       "publicOutcomeLabelDateIndependentlyVerified":False,"predecisionEvidenceVerified":False,
       "modelEligible":False},
      {"applicationId":"BLA761343","source":"OPENFDA_SELECTED_PUBLIC_CRL_LETTERS",
       "sourceRecordSha256":"b"*64,"sourceAction":"COMPLETE RESPONSE",
       "reportedActionDate":"2023-10-11",
       "researchClass":"CRL_EXPLICIT_ORIGINAL",
       "sourceOriginalOrSupplementUnit":"1",
       "sourceApplicationReferences":["BLA 761343/Original 1"],
       "exactReviewCycleIndependentlyVerified":False,
       "publicOutcomeLabelDateIndependentlyVerified":False,"predecisionEvidenceVerified":False,
       "modelEligible":False}
    ]
    raws={k:json.dumps(v,sort_keys=True).encode() for k,v in (("approved",ap),("crl",crl),("candidates",rows))}
    receipt={
      "schema":"MAIN_FDA_PUBLIC_SOURCE_REPLAY_R38",
      "status":"SELECTED_SOURCES_NOT_A_COMPLETE_FDA_COHORT",
      "candidateFileSha256":hashlib.sha256(raws["candidates"]).hexdigest(),
      "researchCandidateRows":len(rows),
      "completeOriginalApplicationFilingRosterVerified":False,
      "modelEligibleHistoricalCases":0,"historicalRealBacktests":0,
      "trainingAuthorized":False,"approvalProbability":None,
      "sourceProvenance":{
       "approvedRegistry":{"sha256":hashlib.sha256(raws["approved"]).hexdigest(),"bytes":len(raws["approved"]),"retrievedOn":"2026-11-09"},
       "selectedCrl":{"sha256":hashlib.sha256(raws["crl"]).hexdigest(),"bytes":len(raws["crl"]),"retrievedOn":"2026-11-09"}
      }
    }
    identity,_=triage(rows,receipt,raws["candidates"],"2026-11-09T19:40:00Z")
    return rows,receipt,raws,ap,crl,identity

def evaluate(parts):
    rows,receipt,raws,approved,crl,identity=parts
    return crosscheck(rows,receipt,raws["candidates"],approved,raws["approved"],
        crl,raws["crl"],identity,"2026-11-09T19:40:00Z")

def refresh_original_snapshot_after_intentional_source_update(parts,kind):
    # An intentional new original source snapshot must be carried through the
    # raw archive and its SHA-256 receipt, unlike an in-memory forgery.
    idx=3 if kind=="approved" else 4
    receipt_key="approvedRegistry" if kind=="approved" else "selectedCrl"
    raw=json.dumps(parts[idx],sort_keys=True).encode()
    parts[2][kind]=raw
    parts[1]["sourceProvenance"][receipt_key]["sha256"]=hashlib.sha256(raw).hexdigest()
    parts[1]["sourceProvenance"][receipt_key]["bytes"]=len(raw)

def refresh_candidate_source_and_identity_after_intentional_update(parts):
    # A modified example postdecision source lead gets a NEW matching source
    # receipt and R48 identity audit; no model eligibility is introduced.
    raw=json.dumps(parts[0],sort_keys=True).encode()
    parts[2]["candidates"]=raw
    parts[1]["candidateFileSha256"]=hashlib.sha256(raw).hexdigest()
    parts[5],_=triage(parts[0],parts[1],raw,"2026-11-09T19:40:00Z")

def test_original_source_crosscheck_accepts_both_published_action_dates_without_cycle_certification():
    r=evaluate(fixture())
    assert r["sourceRecordRows"]==2
    assert r["reconciledOriginalSourceActionRows"]==2
    assert r["reconciledOriginalApplicationApprovalRows"]==1
    assert r["reconciledPublishedCrlRows"]==1
    assert r["publishedCrlWithExplicitOriginalSubmissionReference"]==1
    assert r["r48GroupedParentSourceIdentities"]==1
    assert r["r48MixedApprovalAndCrlParentIdGroups"]==1
    assert r["exactFdaDecisionCyclesIndependentlyAdjudicated"]==0
    assert r["predecisionEvidenceSnapshotsIndependentlyVerified"]==0
    assert r["measuredPredictiveAccuracy"] is None
    assert r["modelTrainingAuthorized"] is False
    assert r["officialFutureFdaForecast"]=="ABSTAIN"
    assert all(x["modelEligible"] is False for x in r["actionSideAuditRecords"])

def test_original_source_fields_cannot_silently_upgrade_source_matches():
    parts=fixture()
    parts[3]["records"][0]["submissions_as_published"][0]["submission_status_date_as_published"]="20240417"
    refresh_original_snapshot_after_intentional_source_update(parts,"approved")
    r=evaluate(parts)
    assert r["unreconciledSourceActionRows"]==1
    assert "ORIGINAL_SUBMISSION_DATE_NUMBER_NOT_UNIQUE_OR_MISMATCH" in r["sourceLinkageProblems"]
    assert r["independentRealHistoricalPredictions"]==0

def test_supplement_approval_cannot_be_promoted_into_original_submission_match():
    parts=fixture()
    parts[3]["records"][0]["submissions_as_published"][0]["submission_type_as_published"]="SUPPL"
    refresh_original_snapshot_after_intentional_source_update(parts,"approved")
    r=evaluate(parts)
    assert r["reconciledOriginalApplicationApprovalRows"]==0
    assert r["reconciledPublishedCrlRows"]==1

def test_mismatch_original_crl_letter_date_is_evidence_gap_not_negative_outcome():
    parts=fixture()
    parts[4]["records"][0]["letter_date_as_published"]="10/12/2023"
    refresh_original_snapshot_after_intentional_source_update(parts,"crl")
    r=evaluate(parts)
    assert r["unreconciledSourceActionRows"]==1
    assert r["sourceLinkageProblems"]=={"ORIGINAL_CRL_LETTER_DATE_MISMATCH":1}
    assert r["calibratedFdaProbability"] is None

@pytest.mark.parametrize("changed",[
 lambda p:p[1]["sourceProvenance"]["approvedRegistry"].update(sha256="0"*64),
 lambda p:p[1]["sourceProvenance"]["selectedCrl"].update(bytes=0),
 lambda p:p[5].update(independentApplicationReviewCyclesVerified=1),
 lambda p:p[5].update(modelTrainingAuthorized=True),
 lambda p:p[3].update(status="COMPLETE_INDEPENDENT_COHORT"),
 lambda p:p[4]["records"][0].update(source_record_sha256="1"*64),
])
def test_forged_archive_provenance_or_parent_research_identity_fails_closed(changed):
    parts=fixture()
    changed(parts)
    with pytest.raises(ValueError):evaluate(parts)

def test_explicit_original_number_mismatch_is_not_certified():
    p=fixture();p[4]["records"][0]["application_numbers"]=["BLA 761343"]
    p[0][1]["sourceApplicationReferences"]=["BLA 761343"]
    refresh_original_snapshot_after_intentional_source_update(p,"crl")
    refresh_candidate_source_and_identity_after_intentional_update(p)
    r=evaluate(p)
    assert r["reconciledPublishedCrlRows"]==0
    assert r["sourceLinkageProblems"]=={"EXPLICIT_ORIGINAL_UNIT_NOT_SUPPORTED_BY_SOURCE":1}

def test_source_action_outcome_payload_never_contains_prediction_or_model_accuracy():
    report=evaluate(fixture())
    assert report["completePublicCrlAndNonapprovalDenominatorVerified"] is False
    assert report["consecutiveOriginalNdaBlaApplicationFilingRosterVerified"] is False
    assert report["productionMutationAuthorized"] is False
    assert report["independentRetrospectiveBacktests"]==0
    for rec in report["actionSideAuditRecords"]:
        assert rec["predictionOrValidationAuthorized"] is False
        assert rec["independentFdaReviewCycleAdjudicated"] is False
