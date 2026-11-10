"""R49: distinguish retrieved-byte changes from scientific materiality."""
from copy import deepcopy
from scripts.research_workstream_history import changed_applications,digest
from scripts.build_focus_source_change_review_r49 import summarize
from scripts.build_focus_research_checkpoint_r47 import collect
from test_parallel_focus_historical_r47 import source_bundle,HASHES
import pytest

AT="2026-11-09T19:00:00Z"

def build():
    old=collect(source_bundle(),HASHES,AT)
    current=deepcopy(old)
    for i in (0,1):
        url="https://www.sec.gov/Archives/edgar/data/111/222/report.htm"
        a=current["applicationResearchRecords"][i]
        a["applicationSourceReferences"]=[{"url":url,"sha256":"b"*64,
                 "retrievalStatus":"FETCHED"}]
        a["sourceVersions"]["applicationSources"]=a["applicationSourceReferences"]
        a["evidenceFingerprint"]=digest(a["sourceVersions"])
        prior=old["applicationResearchRecords"][i]
        prior["applicationSourceReferences"]=[{"url":url,"sha256":"a"*64,
                 "retrievalStatus":"FETCHED"}]
        prior["sourceVersions"]["applicationSources"]=prior["applicationSourceReferences"]
        prior["evidenceFingerprint"]=digest(prior["sourceVersions"])
    review={"clinicalWrites":0,"predictionReleaseAuthorized":False,
            "reassessment":changed_applications(old,current)}
    return old,current,review

def test_shared_fda_source_change_is_one_unique_url_with_two_applications():
    old,cur,review=build()
    r=summarize(review,"1001")
    assert r["applicationResearchRecords"]==23
    assert r["applicationsFlaggedForSourceReview"]==2
    assert r["uniqueSponsorSecOrFdaSourceChanges"]==1
    assert r["registryNctSourceChangeReferences"]==0
    assert r["applicationSourceChangeReferences"][0]["affectedApplicationResearchIds"]==sorted([
        cur["applicationResearchRecords"][i]["applicationCycleId"] for i in (0,1)])
    assert r["applicationSourceChangeReferences"][0]["changeKind"]=="CONTENT_HASH_CHANGED_REQUIRES_REVIEW"
    assert r["newValidatedApplicationPredictions"]==0
    assert r["automaticMaterialClinicalChangeInference"] is False
    assert r["productionWriteAuthorized"] is False

def test_registry_bytes_change_requires_review_without_calibrated_prediction():
    old,cur,review=build()
    c=cur["applicationResearchRecords"][2]
    c["sourceVersions"]["trials"][0]["sourceVersions"]["primary"]="f"*64
    c["evidenceFingerprint"]=digest(c["sourceVersions"])
    review["reassessment"]=changed_applications(old,cur)
    r=summarize(review,"1002")
    assert r["registryNctSourceChangeReferences"]>=1
    assert r["newValidatedApplicationPredictions"]==0
    assert all(x["changeKind"]=="REGISTRY_RAW_BYTES_CHANGED_REQUIRES_REVIEW" for x in r["registrySourceChangeReferences"])

@pytest.mark.parametrize("mutate",[
 lambda r:r.update(clinicalWrites=1),
 lambda r:r.update(predictionReleaseAuthorized=True),
 lambda r:r["reassessment"].pop(),
 lambda r:r["reassessment"][0].update(materialScientificChangeAdjudicated=True),
 lambda r:r["reassessment"][0].update(authorizedGradesOrPredictionsModified=True),
 lambda r:r["reassessment"][0].update(applicationCycleId=r["reassessment"][1]["applicationCycleId"]),
 lambda r:r["reassessment"][0].update(state="CLINICAL_RESULT_PROVED"),
 lambda r:r["reassessment"][0].update(reassessmentRequired="yes"),
])
def test_source_review_never_accepts_a_false_clinical_release(mutate):
    _,_,r=build();mutate(r)
    with pytest.raises(ValueError):summarize(r,"1002")

def test_unmodified_reassessment_has_zero_source_byte_changes():
    s=collect(source_bundle(),HASHES,AT)
    report={"clinicalWrites":0,"predictionReleaseAuthorized":False,
            "reassessment":changed_applications(s,deepcopy(s))}
    r=summarize(report,"1003")
    assert r["uniqueSponsorSecOrFdaSourceChanges"]==0
    assert r["registryNctSourceChangeReferences"]==0
    assert r["applicationsFlaggedForSourceReview"]==0
