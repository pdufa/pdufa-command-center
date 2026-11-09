"""R55 source primary/AE/method packets; never automatically approve or rank."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import pytest
from test_focus_methods_crosswalk_r54 import fixture,MEASURE
from scripts.build_focus_methods_crosswalk_r54 import build as build_methods
from scripts.assemble_focus_clinical_review_packets_r55 import assemble

def scenario(tmp_path):
    m,r53,pdf,registry=fixture(tmp_path)
    ids={r["nct"]:[] for r in m["trialRows"]}
    for g in m["applicationGroups"]:
        for n in g["ncts"]:ids[n].append(g["cycleId"])
    for nct in ids:
        path=registry/(nct+".json")
        if not path.exists():
            path.write_text(json.dumps({"protocolSection":{"identificationModule":{"nctId":nct},
                         "outcomesModule":{"primaryOutcomes":[{"measure":MEASURE,"timeFrame":"Week 24"}]}}}))
    nct="NCT04544293"
    path=registry/(nct+".json")
    study=json.loads(path.read_bytes())
    study["resultsSection"]={
     "outcomeMeasuresModule":{"outcomeMeasures":[{
       "type":"PRIMARY","title":MEASURE,"timeFrame":"Week 24",
       "groups":[{"id":"OG000","title":"Molgramostim"},{"id":"OG001","title":"Placebo"}],
       "analyses":[{"groupIds":["OG000","OG001"],
                    "pValue":"0.0007","statisticalMethod":"Mixed Models Analysis",
                    "paramType":"Mean Difference (Net)","paramValue":"6.0",
                    "ciPctValue":"95","ciLowerLimit":"2.5","ciUpperLimit":"9.4"}]
     }]},
     "adverseEventsModule":{"eventGroups":[
       {"id":"EG000","title":"Molgramostim","seriousNumAffected":14,"seriousNumAtRisk":81,
        "deathsNumAffected":0,"deathsNumAtRisk":81},
       {"id":"EG001","title":"Placebo","seriousNumAffected":20,"seriousNumAtRisk":83,
        "deathsNumAffected":0,"deathsNumAtRisk":83}],
       "seriousEvents":[{"term":"Pneumonia"}],"otherEvents":[{"term":"Headache"}]
     }}
    path.write_text(json.dumps(study))
    r54=build_methods(m,r53,pdf,registry)
    source_r46={"schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
       "nctCount":29,"applicationGroupCount":23,"records":[]}
    for nct in ids:
        data=(registry/(nct+".json")).read_bytes()
        source_r46["records"].append({
          "nct":nct,"applicationCycleIds":ids[nct],
          "sourceResponseSha256":hashlib.sha256(data).hexdigest(),
          "sourceResponseBytes":len(data)
        })
    return m,r54,source_r46,registry

def test_source_linked_29_trial_23_application_review_packet_with_real_reported_stat_fields(tmp_path):
    m,r54,r46,registry=scenario(tmp_path)
    result=assemble(m,r46,r54,registry)
    assert result["nctTrials"]==29 and result["applicationGroups"]==23
    assert result["sourceVerifiedCurrentProtocolSAPDocuments"]==23
    assert result["postedPrimaryTables"]==1
    assert result["reportedPrimaryStatisticalComparisons"]==1
    assert result["uniqueTrialsWithPostedPrimary"]==1
    assert result["uniqueTrialsWithPostedAdverseEvents"]==1
    assert result["seriousAeTermRows"]==1
    assert result["otherAeTermRows"]==1
    assert len(result["currentSourceCasePackets"])==23
    assert len(result["originalUniqueTrialEvidence"])==29
    assert result["historicalLockedSAPsIndependentlyVerified"]==0
    assert result["signedScientificReviews"]==0
    assert result["independentlyValidatedFDAApplicationForecasts"]==0
    assert result["measuredAccuracy"] is None
    assert result["modelTrainingAuthorized"] is False
    assert result["clinicalOrProductionWrites"] is False
    assert result["officialPendingFDAOutcome"]=="ABSTAIN"
    a=next(x for x in result["originalUniqueTrialEvidence"] if x["nct"]=="NCT04544293")
    comparison=a["postedPrimaryOutcomeTables"][0]["statisticalComparisons"][0]
    assert comparison["reportedPValueLiteral"]=="0.0007"
    assert comparison["reportedEstimateLiteral"]=="6.0"
    assert comparison["reportedLowerBoundLiteral"]=="2.5"
    assert comparison["reportedUpperBoundLiteral"]=="9.4"
    assert comparison["independentStatisticalRecalculationComplete"] is False
    assert a["postedAdverseEventArmCountsAsReported"][0]["seriousAffected"]==14
    assert a["postedAdverseEventArmCountsAsReported"][0]["seriousAtRisk"]==81
    assert a["postedAdverseEventArmCountsAsReported"][1]["seriousAffected"]==20
    assert a["postedAdverseEventArmCountsAsReported"][1]["seriousAtRisk"]==83
    assert len(a["sourceMethodsPageReferences"])==2
    assert a["officialFDAOutcomeForecast"]=="ABSTAIN"

def test_17_trials_without_pdf_attachments_are_not_failed_or_assigned_probability(tmp_path):
    m,r54,r46,registry=scenario(tmp_path)
    out=assemble(m,r46,r54,registry)
    capr=next(x for x in out["currentSourceCasePackets"] if x["applicationCycleId"]=="capr-deramiocel")
    assert capr["linkedCurrentProtocolSAPDocs"]==0
    assert capr["fdaProbability"] is None
    assert capr["officialFDAOutcomePrediction"]=="ABSTAIN"
    missing=next(x for x in out["originalUniqueTrialEvidence"] if x["nct"]=="NCT05126758")
    assert missing["trialResultsUnavailableInCurrentRegistryNotFailure"] is True
    assert missing["sourceMethodsPageReferences"]==[]

def test_trial_linked_to_two_application_groups_is_unique_in_evidence_source(tmp_path):
    m,r54,r46,registry=scenario(tmp_path)
    out=assemble(m,r46,r54,registry)
    nct="NCT02500381"
    assert sum(r["nct"]==nct for r in out["originalUniqueTrialEvidence"])==1
    assert sum(nct in a["exactNcts"] for a in out["currentSourceCasePackets"])==2

@pytest.mark.parametrize("modify",[
  lambda r46,r54:r46.update(nctCount=30),
  lambda r46,r54:r54.update(applicationGroups=22),
  lambda r46,r54:r46["records"][0].update(sourceResponseSha256="a"*64),
  lambda r46,r54:r46["records"][0].update(nct="NCT99999999"),
  lambda r46,r54:r54["trialMethodsReview"][0].update(nct="NCT99999999"),
  lambda r46,r54:r54["trialMethodsReview"][0].update(applicationCycleIds=["other"]),
  lambda r46,r54:r54.update(independentlySignedClinicalMethodGrades=1),
  lambda r46,r54:r54.update(clinicalOrProductionWrites=True),
  lambda r46,r54:r54["trialMethodsReview"][0].update(sourceDocumentCount=999),
])
def test_forged_source_receipt_clinical_score_or_id_mismatch_fails_closed(tmp_path,modify):
    m,r54,r46,registry=scenario(tmp_path);modify(r46,r54)
    with pytest.raises(ValueError):assemble(m,r46,r54,registry)

def test_original_registry_source_byte_tamper_fatal(tmp_path):
    m,r54,r46,registry=scenario(tmp_path)
    path=registry/"NCT04544293.json"
    path.write_bytes(path.read_bytes()+b" ")
    with pytest.raises(ValueError,match="ORIGINAL_REGISTRY_RECEIPT_MISMATCH"):
        assemble(m,r46,r54,registry)

def test_comparisons_unknown_is_not_false_negative_or_fda_rejection(tmp_path):
    m,r54,r46,registry=scenario(tmp_path)
    nct="NCT04544293"
    path=registry/(nct+".json")
    trial=json.loads(path.read_text())
    trial["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["analyses"]=None
    path.write_text(json.dumps(trial))
    for r in r46["records"]:
        if r["nct"]==nct:
            data=path.read_bytes()
            r["sourceResponseSha256"]=hashlib.sha256(data).hexdigest()
            r["sourceResponseBytes"]=len(data)
    trial_row=next(t for t in r54["trialMethodsReview"] if t["nct"]==nct)
    trial_row["currentRegistrySourceSha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
    out=assemble(m,r46,r54,registry)
    a=next(t for t in out["originalUniqueTrialEvidence"] if t["nct"]==nct)
    assert a["reportedPrimaryStatisticalComparisons"]==0
    assert a["postedPrimaryOutcomeTables"][0]["statisticalComparisons"]==[]
    assert a["officialFDAOutcomeForecast"]=="ABSTAIN"
