"""R47 parallel research lanes: source-first, failure-isolated, 0 inflated forecasts."""
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_focus_research_checkpoint_r47 import collect,canonical_manifest
from scripts.build_historical_source_checkpoint_r47 import verify

MANIFEST=canonical_manifest()
NCTS=sorted(r["nct"] for r in MANIFEST["trialRows"])
CROSSWALK={n:sorted(g["cycleId"] for g in MANIFEST["applicationGroups"] if n in g["ncts"]) for n in NCTS}
HASHES={"primary":"a"*64,"safety":"b"*64,"documents":"c"*64}
def source_bundle():
    p={"schema":"MAIN_R42_29_TRIAL_REGISTRY_PRIMARY_EVIDENCE",
       "nctCount":29,"applicationGroupCount":23,"records":[]}
    s={"schema":"MAIN_R44_EXACT_NCT_POSTED_SAFETY_SOURCE_V1",
       "nctCount":29,"provisionalApplicationCount":23,"records":[]}
    d={"schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
       "nctCount":29,"applicationGroupCount":23,"records":[]}
    for i,nct in enumerate(NCTS):
        p["records"].append({"nct":nct,"sourceResponseSha256":"1"*64,
          "postedPrimaryOutcomeTableCount":1 if i<12 else 0})
        s["records"].append({"nct":nct,"sourceResponseSha256":"2"*64,
          "currentRegistryAdverseEventsModulePresent":i<12,
          "seriousEventTermCount":3 if i<12 else 0})
        d["records"].append({"nct":nct,"sourceResponseSha256":"3"*64,
          "applicationCycleIds":CROSSWALK[nct],
          "currentAttachedDocumentCount":2 if i<12 else 0,
          "currentSapAttachmentPresent":i<12})
    return {"primary":p,"safety":s,"documents":d}

def history_fixture():
    rows=[{"source":"FDA_APPROVED_PRODUCTS","sourceRecordSha256":"a"*64,
        "modelEligible":False,"exactReviewCycleIndependentlyVerified":False,
        "predecisionEvidenceVerified":False,
        "publicOutcomeLabelDateIndependentlyVerified":False}]
    raw=json.dumps(rows,sort_keys=True).encode()
    receipt={"schema":"MAIN_FDA_PUBLIC_SOURCE_REPLAY_R38",
      "status":"SELECTED_SOURCES_NOT_A_COMPLETE_FDA_COHORT",
      "candidateFileSha256":hashlib.sha256(raw).hexdigest(),
      "researchCandidateRows":1,
      "completeOriginalApplicationFilingRosterVerified":False,
      "modelEligibleHistoricalCases":0,
      "historicalRealBacktests":0,
      "trainingAuthorized":False,
      "approvalProbability":None}
    return rows,receipt,raw

def test_focus_builds_full_missing_document_priority_and_does_not_score():
    r=collect(source_bundle(),HASHES,"2026-11-09T19:00:00Z")
    assert r["exactNctCount"]==29 and r["provisionalApplicationCount"]==23
    assert r["trialsWithCurrentPostedPrimaryTables"]==12
    assert r["trialsWithCurrentRegistrySap"]==12
    assert r["trialsMissingAnyRequiredIndependentEvidence"]==29
    assert len(r["rows"])==29
    assert r["rows"][0]["numericalProbability"] is None
    assert r["rows"][-1]["regulatorFdaOutcomePrediction"]=="ABSTAIN"
    assert "NO_CURRENT_REGISTRY_SAP_ATTACHMENT" in r["rows"][-1]["missingEvidenceOrVerification"]
    assert r["validatedFdaApplicationForecasts"]==0
    assert r["modelTrainingAuthorized"] is False
    assert r["productionWriteAuthorized"] is False

@pytest.mark.parametrize("mutate",[
    lambda x:x["primary"].update(nctCount=30),
    lambda x:x["safety"].update(provisionalApplicationCount=29),
    lambda x:x["documents"]["records"].pop(),
    lambda x:x["documents"]["records"][0].update(nct="NCT99999999"),
    lambda x:x["documents"]["records"][0].update(applicationCycleIds=[]),
    lambda x:x["primary"]["records"][0].update(postedPrimaryOutcomeTableCount=-1),
    lambda x:x["documents"]["records"][0].update(currentAttachedDocumentCount=-1),
])
def test_focus_source_identity_count_or_schema_changes_fail_closed(mutate):
    data=source_bundle();mutate(data)
    with pytest.raises(ValueError):collect(data,HASHES,"2026-11-09T19:00:00Z")

def test_historical_source_run_records_real_research_without_claiming_approval_accuracy():
    rows,receipt,raw=history_fixture()
    r=verify(rows,receipt,raw,"2026-11-09T19:00:00Z")
    assert r["researchSourceActionCandidates"]==1
    assert r["pairedIndependentHistory"]==0
    assert r["prospectiveAccuracy"] is None
    assert r["calibration"] is None
    assert r["modelTrainingAuthorized"] is False
    assert r["automaticAccuracyOrHundredPercentClaimAuthorized"] is False
    assert "CONSECUTIVE_FULL_ORIGINAL_APPLICATION_FILING_COHORT" in r["missingGates"]

@pytest.mark.parametrize("mutate",[
  lambda r,doc:doc.update(candidateFileSha256="0"*64),
  lambda r,doc:doc.update(modelEligibleHistoricalCases=1),
  lambda r,doc:doc.update(completeOriginalApplicationFilingRosterVerified=True),
  lambda r,doc:doc.update(approvalProbability=.95),
  lambda r,doc:doc.update(trainingAuthorized=True),
  lambda r,doc:r[0].update(predecisionEvidenceVerified=True),
  lambda r,doc:r[0].update(modelEligible=True),
  lambda r,doc:r[0].update(publicOutcomeLabelDateIndependentlyVerified=True),
])
def test_historical_source_label_or_accuracy_promotion_is_blocked(mutate):
    rows,receipt,raw=history_fixture()
    mutate(rows,receipt)
    with pytest.raises(ValueError):verify(rows,receipt,raw,"2026-11-09T19:00:00Z")


def test_same_size_forged_roster_or_application_groups_are_rejected():
    data=source_bundle()
    for doc in data.values():doc["records"][0]["nct"]="NCT99999999"
    with pytest.raises(ValueError,match="DISAGREEING"):collect(data,HASHES,"2026-11-09T19:00:00Z")
    data=source_bundle();data["documents"]["records"][0]["applicationCycleIds"]=["different-application"]
    with pytest.raises(ValueError,match="MISSING_APP"):collect(data,HASHES,"2026-11-09T19:00:00Z")


def test_all23_application_records_preserve_cutoff_counterevidence_and_abstention():
    r=collect(source_bundle(),HASHES,"2026-11-09T19:00:00Z")
    assert len(r["applicationResearchRecords"])==23
    assert {n for a in r["applicationResearchRecords"] for n in a["ncts"]}==set(NCTS)
    assert all(a["counterevidenceAndGaps"] and a["numericalProbability"] is None for a in r["applicationResearchRecords"])
    assert sum(a["prediction"]=="ABSTAIN" for a in r["applicationResearchRecords"])==22
    assert r["newScientificallyQualifiedResearchPredictions"]==0
