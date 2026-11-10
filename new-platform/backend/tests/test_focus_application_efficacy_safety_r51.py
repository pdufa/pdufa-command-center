"""R51: replay exact current registry primary / adverse-event source fields to all 23 applications.

Synthetic p values test *preservation*, not a conclusion about FDA approvability.
"""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import pytest
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest
from scripts.build_focus_registry_results_r42 import extract as extract_primary
from scripts.build_focus_registry_safety_r44 import extract as extract_safety
from scripts.build_focus_protocol_index_r46 import extract as extract_docs
from scripts.build_focus_application_efficacy_safety_r51 import assess

def fixture(tmp_path):
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    ids={r["nct"]:[] for r in manifest["trialRows"]}
    for g in manifest["applicationGroups"]:
        for n in g["ncts"]:ids[n].append(g["cycleId"])
    sources={
        "primary":{"schema":"MAIN_R42_29_TRIAL_REGISTRY_PRIMARY_EVIDENCE",
          "nctCount":29,"applicationGroupCount":23,"records":[]},
        "safety":{"schema":"MAIN_R44_EXACT_NCT_POSTED_SAFETY_SOURCE_V1",
          "nctCount":29,"provisionalApplicationCount":23,"records":[]},
        "documents":{"schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
          "nctCount":29,"applicationGroupCount":23,"records":[]}
    }
    raws=tmp_path/"original";raws.mkdir()
    for i,nct in enumerate(ids):
        posted=i<12
        study={"protocolSection":{
            "identificationModule":{"nctId":nct},
            "statusModule":{"resultsFirstPostDateStruct":{"date":"2025-08-01"},
                            "lastUpdatePostDateStruct":{"date":"2026-11-01"}},
            "outcomesModule":{"primaryOutcomes":[{"measure":"Change from baseline at Week 24",
                    "timeFrame":"Week 24","description":"Original current registry primary outcome."}]}
        }}
        if posted:
            study["resultsSection"]={
              "outcomeMeasuresModule":{"outcomeMeasures":[
                {"type":"PRIMARY","title":"Change from baseline at Week 24",
                 "timeFrame":"Week 24","unitOfMeasure":"Units",
                 "groups":[{"id":"OG000","title":"Active"},{"id":"OG001","title":"Placebo"}],
                 "classes":[{"categories":[{"measurements":[
                      {"groupId":"OG000","value":"12.2"},{"groupId":"OG001","value":"9.4"}
                 ]}]}],
                 "analyses":[{"groupIds":["OG000","OG001"],"pValue":"0.0007",
                             "statisticalMethod":"Two-sided test"}]}
              ]},
              "adverseEventsModule":{
                "eventGroups":[
                    {"id":"EG000","title":"Active","seriousNumAffected":2,"seriousNumAtRisk":100},
                    {"id":"EG001","title":"Placebo","seriousNumAffected":1,"seriousNumAtRisk":100}
                ],
                "seriousEvents":[{"term":"Pneumonia","organSystem":"Infections",
                  "stats":[{"groupId":"EG000","numAffected":1,"numAtRisk":100},
                           {"groupId":"EG001","numAffected":0,"numAtRisk":100}]}],
                "otherEvents":[{"term":"Headache","organSystem":"Nervous system",
                  "stats":[{"groupId":"EG000","numAffected":4,"numAtRisk":100}]}]
              }}
        study["documentSection"]={"largeDocumentModule":{"largeDocs":[
          {"typeAbbrev":"Prot_SAP","filename":"Prot_SAP_000.pdf",
            "hasProtocol":True,"hasSap":True,"date":"2025-01-02"}]}}
        raw=json.dumps(study,sort_keys=True).encode()
        (raws/(nct+".json")).write_bytes(raw)
        receipt={"url":"https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json",
                "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
        sources["primary"]["records"].append(extract_primary(study,nct,receipt))
        sources["safety"]["records"].append(extract_safety(study,nct,receipt,ids[nct]))
        sources["documents"]["records"].append(extract_docs(study,nct,receipt,ids[nct]))
    return manifest,sources,raws

def test_29_original_ncts_map_into_23_signed_off_only_after_future_review(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    result=assess(manifest,files,raws)
    assert result["trialRosterCount"]==29
    assert result["applicationDossierCount"]==23
    assert len(result["trialEvidence"])==29
    assert len(result["applicationDossiers"])==23
    assert result["uniqueTrialsWithCurrentPrimaryTables"]==12
    assert result["uniqueTrialsWithCurrentAeModule"]==12
    assert result["currentReportedPrimaryStatisticalAnalysisCount"]==12
    assert result["currentReportedSeriousAeTermRows"]==12
    assert result["currentReportedOtherAeTermRows"]==12
    assert result["validatedFDAForecasts"]==0
    assert result["independentScientificGrades"]==0
    assert result["measuredApprovalAccuracy"] is None
    assert result["armSpecificSafetyNoPoolingOrCausality"] is True
    a=result["trialEvidence"][0]
    assert a["primary"][0]["statisticalAnalyses"][0]["pValueAsPublished"]=="0.0007"
    assert a["primaryTitleTimeframeConcordance"][0]["currentRegisteredTitleAndTimeframeExactMatch"] is True
    assert a["primaryTitleTimeframeConcordance"][0]["historicalPreReadoutEndpointHierarchyVerified"] is False
    assert a["eventGroups"][0]["seriousNumAffectedAsReported"]=="2"
    assert a["seriousEventTerms"][0]["term"]=="Pneumonia"
    assert a["forecast"]=="ABSTAIN"
    assert a["clinicalBenefitRiskAdjudicated"] is False
    assert a["currentProtocolSapAttachments"][0]["preReadoutLockedVersionVerified"] is False

def test_same_clinical_trial_may_support_two_application_cycles_without_duplication(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    out=assess(manifest,files,raws)
    nct="NCT02500381"
    row=next(x for x in out["trialEvidence"] if x["nct"]==nct)
    assert set(row["applicationCycleIds"])=={"srpt-casimersen","srpt-golodirsen"}
    assert sum(nct in case["exactNctIds"] for case in out["applicationDossiers"])==2
    assert len({x["nct"] for x in out["trialEvidence"]})==29

def test_registry_safety_not_collapsed_into_pooled_percentages_or_pvalue_claims(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    out=assess(manifest,files,raws)
    record=out["applicationDossiers"][0]
    assert record["numericalFdaProbability"] is None
    assert record["statisticalEfficacyConclusion"]=="NOT_INDEPENDENTLY_ADJUDICATED"
    assert record["causalSafetyConclusion"]=="NOT_INDEPENDENTLY_ADJUDICATED"
    assert record["independentReviewerSignoff"] is False
    assert all(x["originalPreDecisionEvidenceAvailableVerified"] is False
               for x in out["applicationDossiers"])
    assert out["reportedPValuesAreNotMultiplicityValidated"] is True

@pytest.mark.parametrize("mutation",[
 lambda files: files["primary"]["records"][0]["primaryOutcomeTables"][0].update(title="Fraudulent replacement"),
 lambda files: files["primary"]["records"][0]["primaryOutcomeTables"][0]["statisticalAnalyses"][0].update(pValueAsPublished="0.000001"),
 lambda files: files["safety"]["records"][0]["eventGroups"][0].update(seriousNumAffectedAsReported="0"),
 lambda files: files["documents"]["records"][0]["currentDocumentIndex"][0].update(documentDateAsRegistry="2020-01-01"),
 lambda files: files["primary"]["records"][0].update(sourceResponseSha256="0"*64),
 lambda files: files["primary"]["records"][0].update(nct=files["primary"]["records"][1]["nct"]),
 lambda files: files["safety"]["records"][0].update(applicationCycleIds=["another-application"]),
 lambda files: files["documents"]["records"][0].update(currentSapAttachmentPresent=False),
 lambda files: files["safety"].update(provisionalApplicationCount=22),
])
def test_no_falsified_undetected_endpoint_ae_clocks_or_original_roster(tmp_path,mutation):
    manifest,files,raws=fixture(tmp_path);mutation(files)
    with pytest.raises(ValueError):
        assess(manifest,files,raws)

def test_archived_raw_registry_byte_tamper_refused(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    n=manifest["trialRows"][0]["nct"]
    (raws/(n+".json")).write_bytes(b'{"protocolSection":{"identificationModule":{"nctId":"'+n.encode()+b'"}}}')
    with pytest.raises(ValueError,match="ORIGINAL_RAW_REGISTRY_SOURCE_SHA_MISMATCH"):
        assess(manifest,files,raws)

def test_missing_data_is_absent_current_registry_not_negative_trial_result(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    q=files["primary"]["records"][20]
    q.pop("sourceResponseSha256")
    files["safety"]["records"][20].pop("sourceResponseSha256")
    files["documents"]["records"][20].pop("sourceResponseSha256")
    out=assess(manifest,files,raws)
    t=out["trialEvidence"][20]
    assert t["evidenceStatus"]=="SOURCE_NOT_FULLY_RETRIEVED"
    assert t["sourceGap"]=="NO_COMPARABLE_SINGLE_CURRENT_REGISTRY_SNAPSHOT"
    assert t["forecast"]=="ABSTAIN"

def test_posted_primary_title_frame_mismatch_requires_review_not_trial_failure(tmp_path):
    manifest,files,raws=fixture(tmp_path)
    # Replace original current registry announced primary title and re-extract
    # all three full source captures with identical new source bytes.
    nct=manifest["trialRows"][0]["nct"]
    path=raws/(nct+".json")
    study=json.loads(path.read_bytes())
    study["protocolSection"]["outcomesModule"]["primaryOutcomes"][0]["measure"]="Other updated primary endpoint"
    raw=json.dumps(study,sort_keys=True).encode();path.write_bytes(raw)
    receipt={"url":"https://clinicaltrials.gov/api/v2/studies/"+nct+"?format=json",
       "sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
    apps=[g["cycleId"] for g in manifest["applicationGroups"] if nct in g["ncts"]]
    files["primary"]["records"][0]=extract_primary(study,nct,receipt)
    files["safety"]["records"][0]=extract_safety(study,nct,receipt,apps)
    files["documents"]["records"][0]=extract_docs(study,nct,receipt,apps)
    out=assess(manifest,files,raws)
    trial=out["trialEvidence"][0]
    assert trial["primaryTitleTimeframeConcordance"][0]["currentRegisteredTitleAndTimeframeExactMatch"] is False
    group=next(x for x in out["applicationDossiers"] if x["applicationCycleId"]=="abvx-uc")
    assert "CURRENT_POSTED_PRIMARY_TITLE_TIMEFRAME_DOES_NOT_EXACTLY_MATCH_CURRENT_REGISTERED" in group["criticalUnverifiedEvidence"]
    assert group["approvalOrCrlPrediction"]=="ABSTAIN"
