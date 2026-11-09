"""MAIN R46: synthetic registry document metadata and strict no-clinical-grade gates."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_focus_protocol_index_r46 import extract,run

def study(n,docs=True,combined=False):
    x={"protocolSection":{"identificationModule":{"nctId":n},"statusModule":{
       "studyFirstPostDateStruct":{"date":"2021-01-01"},
       "lastUpdatePostDateStruct":{"date":"2026-10-01"}}}}
    if docs:
        items=[{"typeAbbrev":"Prot_SAP","filename":"Prot_SAP_000.pdf","date":"2023-03-03",
                "hasProtocol":True,"hasSap":True}] if combined else [
                {"typeAbbrev":"Prot","filename":"Prot_000.pdf","date":"2024-03-03",
                 "hasProtocol":True,"hasSap":False},
                {"typeAbbrev":"SAP","filename":"SAP_001.pdf","date":"2024-06-04",
                 "hasProtocol":False,"hasSap":True}]
        x["documentSection"]={"largeDocumentModule":{"largeDocs":items}}
    return x

def manifest():
    n=[f"NCT{i:08d}" for i in range(1,30)]
    return {"trialCount":29,"applicationCount":23,"asOf":"2026-11-09",
      "trialRows":[{"nct":q,"registryUrl":"https://clinicaltrials.gov/api/v2/studies/"+q+"?format=json"}
         for q in n],
      "applicationGroups":[{"cycleId":f"a-{i}","ncts":[n[i]]+([n[23+i]] if i<6 else [])}
         for i in range(23)]}

def getter(url):
    n=url.split("?")[0].rsplit("/",1)[-1]
    k=int(n[-8:])
    raw=json.dumps(study(n,docs=(k<=12),combined=(k==12))).encode()
    return {"url":url,"status":"FETCHED","sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)},raw

def test_original_document_attachment_metadata_not_locked_statistical_proof():
    r=extract(study("NCT00000001"),"NCT00000001",{},["a-0"])
    assert r["currentAttachedDocumentCount"]==2
    assert r["currentSapAttachmentPresent"] is True
    assert r["currentProtocolAttachmentPresent"] is True
    assert all(x["documentDateVerifiedAsFirstPublic"] is False for x in r["currentDocumentIndex"])
    assert all(x["preReadoutLockedVersionVerified"] is False for x in r["currentDocumentIndex"])
    assert r["lockedSapAndPrespecifiedMultiplicityVerified"] is False
    assert r["historicalRegistryAmendmentChainVerified"] is False
    assert r["scientificMethodGrade"] is None
    assert r["officialFDAForecast"]=="ABSTAIN"

def test_combined_document_flag_and_no_document_are_not_invented():
    c=extract(study("NCT00000001",combined=True),"NCT00000001",{},["a"])
    assert c["currentAttachedDocumentCount"]==1
    assert c["currentSapAttachmentPresent"] is True
    z=extract(study("NCT00000001",docs=False),"NCT00000001",{},["a"])
    assert z["currentAttachedDocumentCount"]==0
    assert z["attachmentStatus"]=="NO_CURRENT_REGISTRY_ATTACHMENT"

def test_29_23_canonical_roster_and_original_sha_archive(tmp_path):
    r=run(manifest(),getter,tmp_path)
    assert (r["nctCount"],r["applicationGroupCount"],r["registryRecordsFetched"])==(29,23,29)
    assert (r["trialsWithCurrentProtocol"],r["trialsWithCurrentSap"])==(12,12)
    assert (r["attachmentEntries"],r["missingCurrentAttachments"])==(23,17)
    assert r["preReadoutSapVersionsIndependentlyVerified"]==0
    assert r["signedIndependentReviews"]==0
    assert r["scientificGradesWritten"]==0
    assert r["validatedApplicationFdaForecasts"]==0
    assert r["approvalProbability"] is None
    assert r["futureFdaForecast"]=="ABSTAIN"
    assert r["productionOrReviewerWrites"] is False
    for row in r["records"]:
        original=(tmp_path/(row["nct"]+".json")).read_bytes()
        assert hashlib.sha256(original).hexdigest()==row["sourceResponseSha256"]

def test_registry_identity_or_attachment_filename_mismatch_fails_closed(tmp_path):
    with pytest.raises(ValueError,match="NCT_IDENTITY_MISMATCH"):
        extract(study("NCT00000001"),"NCT00000002",{},["a"])
    d=study("NCT00000001")
    d["documentSection"]["largeDocumentModule"]["largeDocs"][0]["filename"]="../../bad.pdf"
    with pytest.raises(ValueError,match="INVALID_ATTACHMENT_NAME"):
        extract(d,"NCT00000001",{},["a"])
    d=study("NCT00000001")
    d["documentSection"]["largeDocumentModule"]["largeDocs"][0]["date"]="not-a-date"
    with pytest.raises(ValueError,match="MALFORMED_ATTACHMENT_DOCUMENT_DATE"):
        extract(d,"NCT00000001",{},["a"])

def test_no_false_negative_when_source_unavailable_and_no_grade(tmp_path):
    def missing(url):return {"url":url,"status":"HTTP_UNAVAILABLE"},None
    r=run(manifest(),missing)
    assert r["registryRecordsFetched"]==0
    assert r["trialsWithCurrentAttachments"]==0
    assert r["validatedApplicationFdaForecasts"]==0
    assert r["scientificGradesWritten"]==0

def test_source_sha_change_is_not_accepted(tmp_path):
    def tamper(url):
        rec,data=getter(url)
        rec["sha256"]="f"*64
        return rec,data
    with pytest.raises(ValueError,match="ORIGINAL_REGISTRY_SHA256_MISMATCH"):
        run(manifest(),tamper,tmp_path)
