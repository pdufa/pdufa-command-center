"""R48: source postdecision action identity is NOT a model-ready FDA cycle."""
import hashlib,json
from copy import deepcopy
import pytest
from scripts.build_historical_source_identity_audit_r48 import triage

def case(app="BLA761303",when="2024-03-22",action="COMPLETE RESPONSE",
         source="a",original="1"):
    return {
      "applicationId":app,"reportedActionDate":when,
      "sourceAction":action,
      "researchClass":"CRL_EXPLICIT_ORIGINAL" if action=="COMPLETE RESPONSE" else "AP_SOURCE_REGISTRY",
      "sourceRecordSha256":source*64,
      "sourceOriginalOrSupplementUnit":original if action=="COMPLETE RESPONSE" else None,
      "sourceOriginalSubmissionNo":original if action=="AP" else None,
      "sourceApplicationReferences":["BLA 761303/Original "+original] if app is not None else ["BL 125806"],
      "exactReviewCycleIndependentlyVerified":False,
      "predecisionEvidenceVerified":False,"publicOutcomeLabelDateIndependentlyVerified":False,
      "modelEligible":False
    }

def fixture():
    rows=[
      case(source="a",original="1"),
      case(source="b",original="2"),
      case(when="2025-07-30",source="c",original="3"),
      case("NDA218785","2025-06-10","AP","d","1"),
      case("NDA218785","2025-06-10","AP","e","2"),
      case("BLA761343","2023-10-11","COMPLETE RESPONSE","f","1"),
      case("BLA761343","2024-04-16","AP","0","1"),
      case(None,"2024-06-14","COMPLETE RESPONSE","1","1")
    ]
    raw=json.dumps(rows,sort_keys=True).encode()
    receipt={
      "schema":"MAIN_FDA_PUBLIC_SOURCE_REPLAY_R38",
      "status":"SELECTED_SOURCES_NOT_A_COMPLETE_FDA_COHORT",
      "candidateFileSha256":hashlib.sha256(raw).hexdigest(),
      "researchCandidateRows":len(rows),
      "completeOriginalApplicationFilingRosterVerified":False,
      "modelEligibleHistoricalCases":0,
      "historicalRealBacktests":0,
      "trainingAuthorized":False,
      "approvalProbability":None
    }
    return rows,receipt,raw

def test_non_independent_8_action_rows_are_only_4_parent_source_identity_groups():
    rows,receipt,raw=fixture()
    a,n=triage(rows,receipt,raw,"2026-11-09T18:20:00Z")
    assert a["sourceActionRecords"]==8
    assert a["sourceIdentityGroups"]==4
    assert a["standardParentApplicationIds"]==3
    assert a["unresolvedSourceIdentityGroups"]==1
    assert a["knownParentGroupsWithMultipleSourceRows"]==3
    assert a["knownParentGroupsWithMixedApprovalAndCrlSourceTypes"]==1
    assert a["knownParentGroupsWithMultipleCrlRows"]==1
    assert a["knownParentGroupsWithSameDayMultipleSourceRows"]==2
    assert a["independentApplicationReviewCyclesVerified"]==0
    assert a["measuredAccuracy"] is None
    assert n["modelTrainingAuthorized"] is False
    assert n["outcomeVaultAccessControlEstablished"] is False
    assert n["futureForecasterMayConsumeThisWorklist"] is False
    assert n["independentRetrospectiveBacktests"]==0
    assert a["records"][0]["modelEligible"] is False

def test_nonforecast_identity_worklist_has_no_outcome_labels_action_dates_or_probabilities():
    rows,receipt,raw=fixture()
    a,n=triage(rows,receipt,raw,"2026-11-09T18:20:00Z")
    labels={"sourceAction","reportedActionDate","reportedOriginalOrSupplementUnit",
            "observedPublishedActionSourceRecords","mixedPublishedActionTypes"}
    for item in n["records"]:
        assert not labels.intersection(item)
        assert item["sourceSelectedByObservedFdaAction"] is True
        assert item["outcomeBlindForecastInputEligible"] is False
        assert item["officialFdaForecast"]=="ABSTAIN"
        assert item["supportingNctIds"]==[]
    b=next(x for x in a["records"] if x["parentApplicationResearchId"]=="BLA761303")
    assert b["sourceRowCount"]==3
    assert b["multipleOriginalUnitsOrSameDayActions"] is True
    assert b["independentlyVerifiedDecisionCycles"]==0

@pytest.mark.parametrize("mutate",[
  lambda r,c:c.update(candidateFileSha256="1"*64),
  lambda r,c:c.update(completeOriginalApplicationFilingRosterVerified=True),
  lambda r,c:r[0].update(modelEligible=True),
  lambda r,c:r[0].update(exactReviewCycleIndependentlyVerified=True),
  lambda r,c:r[0].update(reportedActionDate="2030-01-01"),
  lambda r,c:r[0].update(sourceAction="FORMAL_EXTENSION"),
  lambda r,c:r[0].update(sourceRecordSha256="insecure"),
  lambda r,c:r[0].update(applicationId="BLA something"),
  lambda r,c:r[0].update(sourceApplicationReferences=[""]),
])
def test_tamper_false_eligibility_or_false_regulatory_action_refused(mutate):
    rows,rec,raw=fixture();mutate(rows,rec)
    with pytest.raises(ValueError):triage(rows,rec,raw,"2026-11-09T18:20:00Z")

def test_exact_duplicate_fda_source_action_refused():
    rows,rec,raw=fixture()
    rows[1]=deepcopy(rows[0])
    with pytest.raises(ValueError,match="DUPLICATED_ORIGINAL_SOURCE_ACTION"):
        triage(rows,rec,raw,"2026-11-09T18:20:00Z")

def test_empty_source_group_is_not_accepted_as_independent_cohort():
    rows,rec,raw=fixture()
    rec["researchCandidateRows"]=0
    with pytest.raises(ValueError):
        triage([],rec,raw,"2026-11-09T18:20:00Z")
