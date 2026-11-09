"""R57: strict original registered endpoint + SAE + SAP provenance guards."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import fitz,pytest
import scripts.build_svra_primary_safety_sap_evidence_r57 as r57

def fake_pdf(pages,markers):
    doc=fitz.open()
    for n in range(1,pages+1):
        p=doc.new_page()
        words=markers.get(n,"Factual study protocol document. No medical verdict.")
        p.insert_text((50,65),words,fontsize=10)
    data=doc.tobytes();doc.close()
    return data

def source_bundle(monkeypatch):
    prot=fake_pdf(72,{51:"average of the two best efforts",70:"alpha-splitting"})
    sap=fake_pdf(32,{25:"one primary efficacy endpoint and seven secondary",
         26:"DLCO at Week 24 is tested. Hochberg method.",
         27:"control-based imputation"})
    originals={r57.PROT:prot,r57.SAP:sap}
    exp={
      r57.PROT:{"sha256":hashlib.sha256(prot).hexdigest(),"pages":72},
      r57.SAP:{"sha256":hashlib.sha256(sap).hexdigest(),"pages":32}
    }
    monkeypatch.setattr(r57,"EXPECTED",exp)
    groups=[{"id":"OG000","title":"Molgramostim"},{"id":"OG001","title":"Placebo"}]
    primary={"type":"PRIMARY","title":"DLCO Week24","timeFrame":"Week 24",
     "groups":groups,"analyses":[{"groupIds":["OG000","OG001"],
     "pValue":"0.0007","statisticalMethod":"Mixed Models Analysis",
     "ciPctValue":"95","ciNumSides":"TWO_SIDED",
     "paramValue":"6.0","ciLowerLimit":"2.5","ciUpperLimit":"9.4",
     "statisticalComment":"Source MMRM model"}]}
    secondary={"type":"SECONDARY","title":"Week48 DLCO",
     "timeFrame":"Week 48","groups":groups,
     "analyses":[{"groupIds":["OG000","OG001"],"pValue":"0.0008",
       "paramValue":"6.9","ciLowerLimit":"2.9","ciUpperLimit":"10.9"}]}
    ae={"eventGroups":[
     {"id":"EG000","title":"Molgramostim",
      "seriousNumAffected":14,"seriousNumAtRisk":81,"otherNumAffected":69,
      "otherNumAtRisk":81,"deathsNumAffected":0,"deathsNumAtRisk":81},
     {"id":"EG001","title":"Placebo",
      "seriousNumAffected":20,"seriousNumAtRisk":83,"otherNumAffected":71,
      "otherNumAtRisk":83,"deathsNumAffected":0,"deathsNumAtRisk":83}
    ]}
    registry={"protocolSection":{"identificationModule":{"nctId":r57.NCT},
          "statusModule":{"resultsFirstPostDateStruct":{"date":"2025-08-07"}}},
          "resultsSection":{"outcomeMeasuresModule":{"outcomeMeasures":[primary,secondary]},
                           "adverseEventsModule":ae}}
    raw=json.dumps(registry,sort_keys=True).encode()
    saved={
        "schema":r57.SCHEMAS["r55"],"nctTrials":29,"applicationGroups":23,
        "sourceVerifiedCurrentProtocolSAPDocuments":23,
        "independentlyValidatedFDAApplicationForecasts":0,
        "clinicalOrProductionWrites":False,
        "originalUniqueTrialEvidence":[
           {"nct":r57.NCT,"applicationCycleIds":[r57.APP],
            "currentRegistrySourceSha256":hashlib.sha256(raw).hexdigest(),
            "reportedPrimaryStatisticalComparisons":1,
            "postedPrimaryOutcomeTables":[{
             "titleAsPosted":"DLCO Week24","timeFrameAsPosted":"Week 24",
             "statisticalComparisons":[{
              "reportedPValueLiteral":"0.0007","reportedEstimateLiteral":"6.0",
              "reportedLowerBoundLiteral":"2.5","reportedUpperBoundLiteral":"9.4",
              "nominalOrAdjustedStatusIndependentlyVerified":False
             }]}],
            "resultsFirstPostedDateFromCurrentRecord":"2025-08-07",
            "postedAdverseEventArmCountsAsReported":[
             {"groupId":v["id"],"seriousAffected":v["seriousNumAffected"],
              "seriousAtRisk":v["seriousNumAtRisk"],
              "otherAffected":v["otherNumAffected"],"otherAtRisk":v["otherNumAtRisk"],
              "deathsAffected":v["deathsNumAffected"],"deathsAtRisk":v["deathsNumAtRisk"]}
             for v in ae["eventGroups"]]}
        ]+[{"nct":"NCT"+str(n).zfill(8)} for n in range(1,29)],
        "currentSourceCasePackets":[{"applicationCycleId":r57.APP,"exactNcts":[r57.NCT]}]
           +[{"applicationCycleId":"group-"+str(n),"exactNcts":[]} for n in range(22)]
    }
    r53={"schema":r57.SCHEMAS["r53"],
         "nctRosterCount":29,"applicationGroupCount":23,
         "originalPdfBodiesRetrieved":23,"validatedFDAForecasts":0}
    r56={"schema":r57.SCHEMAS["r56"],
         "nct":r57.NCT,"applicationCycleId":r57.APP,
         "totalReviewItems":10,"explicitDiscrepancyReconciliationItems":6,
         "preReadoutOriginalSignedSapVersionsVerified":0,
         "independentlyValidatedApplicationFDAForecasts":0,
         "officialFDAOutcomePrediction":"ABSTAIN",
         "verifiedCurrentPublicDocuments":[
            {"file":k,"originalSha256":hashlib.sha256(v).hexdigest(),
             "firstPublicPostingDateIndependentlyVerified":False}
             for k,v in originals.items()],
         "pageAnchoredSourceReviewItems":[{"id":"REVIEW-"+str(n)} for n in range(10)]
    }
    return r53,saved,r56,raw,originals

def test_r57_source_recorded_primary_and_two_real_ae_denominators(monkeypatch):
    params=source_bundle(monkeypatch)
    r=r57.build(*params)
    assert r["schema"]=="MAIN_R57_SAVARA_SOURCE_PRIMARY_SAFETY_SAP_HIERARCHY_EVIDENCE"
    assert r["sourceReportedPrimaryEndpoint"]["reportedPValue"]=="0.0007"
    assert r["sourceReportedPrimaryEndpoint"]["reportedDifferenceVersusPlacebo"]=="6.0"
    assert r["sourceReportedPrimaryEndpoint"]["reported95Ci"]==["2.5","9.4"]
    assert r["sourceReportedPrimaryEndpoint"]["familyWiseAdjustedSignificanceValidated"] is False
    assert r["secondaryComparisonCount"]==1
    assert r["sourceReportedSecondaryComparisons"][0]["familyWiseAdjustedPValueOrClaim"] is None
    arms={x["groupName"]:x for x in r["sourceReportedSafetyExposureArms"]}
    assert arms["Molgramostim"]["sourceReportedAffectedAndDenominators"]["seriousNumAffected"]==14
    assert arms["Placebo"]["sourceReportedAffectedAndDenominators"]["seriousNumAtRisk"]==83
    assert r["verifiedProspectiveSapAndAmendmentTimeline"] is False
    assert r["independentSignedEfficacyAssessment"] is False
    assert r["independentlyValidatedFdaPrediction"] is False
    assert r["scientificGrade"] is None
    assert r["approvalProbability"] is None
    assert r["measuredAccuracy"] is None
    assert r["officialFdaOutcomeAndDelayPrediction"]=="ABSTAIN"
    assert len(r["sapPlanPageCitations"])==4 and len(r["protocolPlanPageCitations"])==2

@pytest.mark.parametrize("edit,expect",[
 (lambda r53,r55,r56,raw,docs:r55.update(independentlyValidatedFDAApplicationForecasts=1),"UNQUALIFIED"),
 (lambda r53,r55,r56,raw,docs:r56.update(totalReviewItems=9),"UNQUALIFIED"),
 (lambda r53,r55,r56,raw,docs:r56.update(officialFDAOutcomePrediction="APPROVAL"),"UNQUALIFIED"),
 (lambda r53,r55,r56,raw,docs:r56["verifiedCurrentPublicDocuments"][0].update(firstPublicPostingDateIndependentlyVerified=True),"R56_SOURCE_DOCUMENT"),
 (lambda r53,r55,r56,raw,docs:r55["originalUniqueTrialEvidence"][0]["postedPrimaryOutcomeTables"][0]["statisticalComparisons"][0].update(reportedPValueLiteral="0.01"),"R55_PRIMARY_STATISTICS"),
 (lambda r53,r55,r56,raw,docs:r55["originalUniqueTrialEvidence"][0]["postedAdverseEventArmCountsAsReported"][0].update(seriousAffected=1),"R55_AE_DENOMINATOR"),
 (lambda r53,r55,r56,raw,docs:r55["originalUniqueTrialEvidence"][0].update(currentRegistrySourceSha256="f"*64),"SVRA_CURRENT_REGISTRY_ORIGINAL_SHA"),
 (lambda r53,r55,r56,raw,docs:docs.update({r57.SAP:docs[r57.SAP]+b"spoof"}),"R56_SOURCE_DOCUMENT_OR_FIRST_PUBLIC_CERTIFICATION_INVALID"),
 ])
def test_no_forged_clinical_provenance_or_statistical_result(monkeypatch,edit,expect):
    params=list(source_bundle(monkeypatch))
    edit(*params)
    with pytest.raises(ValueError,match=expect):
        r57.build(*params)

def test_missing_or_unreliable_sap_phrase_blocks_record(monkeypatch):
    params=list(source_bundle(monkeypatch))
    altered=fake_pdf(32,{25:"one primary efficacy endpoint and seven secondary",
                       26:"DLCO at Week 24 is tested. Hochberg method.",
                       27:"imputation is not described"})
    params[4][r57.SAP]=altered
    params[2]["verifiedCurrentPublicDocuments"][1]["originalSha256"]=hashlib.sha256(altered).hexdigest()
    r57.EXPECTED[r57.SAP]["sha256"]=hashlib.sha256(altered).hexdigest()
    with pytest.raises(ValueError,match="REQUIRED_SAP_WORDING_MISSING"):
        r57.build(*params)

def test_AE_affected_cannot_exceed_population_at_risk(monkeypatch):
    params=list(source_bundle(monkeypatch))
    # Re-sign source result bytes and review receipt only to isolate numerical guard.
    raw=json.loads(params[3])
    raw["resultsSection"]["adverseEventsModule"]["eventGroups"][0]["seriousNumAffected"]=999
    changed=json.dumps(raw,sort_keys=True).encode()
    params[3]=changed
    params[1]["originalUniqueTrialEvidence"][0]["currentRegistrySourceSha256"]=hashlib.sha256(changed).hexdigest()
    params[1]["originalUniqueTrialEvidence"][0]["postedAdverseEventArmCountsAsReported"][0]["seriousAffected"]=999
    with pytest.raises(ValueError,match="AFFECTED_EXCEEDS_RISK_SET"):
        r57.build(*params)
