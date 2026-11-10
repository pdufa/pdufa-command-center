"""R56: source-anchored clinical method reconciliation, not approval scoring."""
from __future__ import annotations
import hashlib
from copy import deepcopy
import fitz,pytest
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest
from scripts.reconcile_savara_methods_r56 import reconcile,NCT,APP

PROTOCOL=[
 "estimated treatment effect week 24 p-value",
 "full analysis set (fas) all subjects randomized",
 "general linear mixed model repeated measurements",
 "type i error control sequential testing",
 "control-based rule missing",
 "safety analysis set analyzed according",
]
SAP=[
 "primary null hypothesis week 24",
 "full analysis set (fas) all randomized subjects",
 "mixed model for repeated measurements control-based imputation",
 "sequential testing alpha splitting",
 "control-based imputation 50 complete datasets",
 "safety analysis set (safs) treatment received",
 "average of the two best all single acceptable",
 "alpha_1 alpha_2 do not fully match",
 "frequency of serious adrs frequency of serious treatment-related aes",
]

def pdf(n,lines,remove=None):
    doc=fitz.open()
    for i in range(n):
        page=doc.new_page()
        if i==19:
            for index,line in enumerate(lines):
                if line==remove:continue
                page.insert_text((55,45+index*23),line,fontsize=10)
    data=doc.tobytes()
    doc.close()
    return data

def fixture(tmp_path,without_sap_phrase=None):
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    ncts=[x["nct"] for x in manifest["trialRows"]]
    group_by_nct={n:[] for n in ncts}
    for app in manifest["applicationGroups"]:
        for n in app["ncts"]:group_by_nct[n].append(app["cycleId"])
    chosen=[NCT]+[n for n in ncts if n!=NCT][:11]
    directory=tmp_path/"original";directory.mkdir()
    hashes={}
    for filename,lines,length in [("Prot_000.pdf",PROTOCOL,134),
                                   ("SAP_001.pdf",SAP,89)]:
        buf=pdf(length,lines,without_sap_phrase if filename=="SAP_001.pdf" else None)
        (directory/(NCT+"-"+filename)).write_bytes(buf)
        hashes[filename]=hashlib.sha256(buf).hexdigest()
    r54={"schema":"MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX",
       "canonicalTrials":29,"applicationGroups":23,
       "currentPdfDocumentsSourceVerified":23,
       "historicalLockedSapVersionsIndependentlyVerified":0,
       "independentlyValidatedApplicationFdaPredictions":0,
       "modelTrainingAuthorized":False,
       "applicationMethodsReview":[{"applicationCycleId":g["cycleId"]} for g in manifest["applicationGroups"]],
       "trialMethodsReview":[]}
    r55={"schema":"MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS",
      "nctTrials":29,"applicationGroups":23,
      "sourceVerifiedCurrentProtocolSAPDocuments":23,
      "independentlyValidatedFDAApplicationForecasts":0,
      "signedScientificReviews":0,"modelTrainingAuthorized":False,
      "currentSourceCasePackets":[{"applicationCycleId":g["cycleId"]}
                                 for g in manifest["applicationGroups"]],
      "originalUniqueTrialEvidence":[]}
    for n in ncts:
        docs=[]
        if n in chosen:
            filenames=["Prot_000.pdf","SAP_001.pdf"] if n!=chosen[-1] else ["Prot_SAP_000.pdf"]
            for name in filenames:
                docs.append({
                 "filename":name,
                 "protocolFlagFromCurrentRegistry":name!="SAP_001.pdf",
                 "sapFlagFromCurrentRegistry":name!="Prot_000.pdf",
                 "sourceUrl":f"https://cdn.clinicaltrials.gov/large-docs/{n[-2:]}/{n}/{name}",
                 "sourceSha256":hashes[name] if n==NCT else "b"*64,
                 "currentRegistryDocumentDateAsReported":
                     ("2024-10-09" if name=="Prot_000.pdf" else "2024-04-24") if n==NCT
                     else "2023-05-01"
                })
        r54["trialMethodsReview"].append({
          "nct":n,"applicationCycleIds":sorted(group_by_nct[n]),
          "sourceDocumentCount":len(docs),"documents":docs,
          "currentRegistrySourceSha256":"a"*64,
          "independentStatisticalReviewComplete":False})
        r55["originalUniqueTrialEvidence"].append({
           "nct":n,"applicationCycleIds":sorted(group_by_nct[n]),
           "currentRegistrySourceSha256":"a"*64,
           "sourceMethodsPageReferences":[{"filename":d["filename"],"sha256":d["sourceSha256"]}
                                          for d in docs],
           "postedPrimaryOutcomeTables":[{"statisticalComparisons":[{
              "reportedPValueLiteral":"0.0007",
              "reportedEstimateLiteral":"6.0",
              "reportedLowerBoundLiteral":"2.5",
              "reportedUpperBoundLiteral":"9.4"}]}] if n==NCT else [],
           "postedAdverseEventArmCountsAsReported":[
              {"groupId":"EG000","groupName":"Molgramostim",
               "seriousAffected":14,"seriousAtRisk":81},
              {"groupId":"EG001","groupName":"Placebo",
               "seriousAffected":20,"seriousAtRisk":83}] if n==NCT else []
        })
    return r54,r55,directory

def test_savara_six_paired_method_categories_and_three_actual_sap_exceptions(tmp_path):
    a,b,path=fixture(tmp_path)
    r=reconcile(a,b,path)
    assert r["canonicalTrials"]==29 and r["applicationGroups"]==23
    assert r["trialCasesWithCurrentProtocolAndSap"]==12
    assert r["trialsWithSapDocumentDatedBeforeAttachedProtocol"]>=1
    assert len(r["trialDocumentChronologyResearch"])==29
    assert r["savara"]["applicationCycleId"]==APP
    assert r["savara"]["laterProtocolDateThanSap"] is True
    assert len(r["savara"]["pairedMethodDescriptionFindings"])==6
    assert len(r["savara"]["explicitSapReportedProtocolDifferences"])==3
    assert r["savara"]["currentRegistryPrimaryOutcome"]["pValueAsPublished"]=="0.0007"
    assert r["savara"]["currentRegistryPrimaryOutcome"]["publishedNumericalPBelowNominalTwoSidedAlphaPointZeroFive"] is True
    assert [(x["seriousAffectedAsReported"],x["seriousAtRiskAsReported"])
            for x in r["savara"]["currentRegistryReportedSafetyArms"]]==[(14,81),(20,83)]
    assert r["savara"]["independentStatisticalAnalystSigned"] is False
    assert r["savara"]["scientificGrade"] is None
    assert r["savara"]["numericalFDAProbability"] is None
    assert r["savara"]["officialOutcomeAndDelayPrediction"]=="ABSTAIN"
    assert r["independentScientificSignoffs"]==0
    assert r["validatedFDAForecasts"]==0
    assert r["measuredFDAAccuracy"] is None
    assert r["modelTrainingAuthorized"] is False
    assert r["productionOrClinicalLedgerWrites"] is False
    for x in r["savara"]["pairedMethodDescriptionFindings"]:
        assert x["protocolSource"]["pdfPageOneBased"]>=1
        assert x["sapSource"]["pdfPageOneBased"]>=1
        assert x["prespecificationAndModelAdequacyIndependentlyValidated"] is False

@pytest.mark.parametrize("tamper",[
  lambda a,b:a.update(independentlyValidatedApplicationFdaPredictions=1),
  lambda a,b:b.update(signedScientificReviews=1),
  lambda a,b:b.update(modelTrainingAuthorized=True),
  lambda a,b:b["originalUniqueTrialEvidence"].pop(),
  lambda a,b:a["trialMethodsReview"][0].update(nct=NCT),
  lambda a,b:next(x for x in a["trialMethodsReview"] if x["nct"]==NCT)["documents"][0].update(sourceSha256="0"*64),
  lambda a,b:next(x for x in a["trialMethodsReview"] if x["nct"]==NCT)["documents"][0].update(currentRegistryDocumentDateAsReported="2031-01-01"),
  lambda a,b:next(x for x in b["originalUniqueTrialEvidence"] if x["nct"]==NCT)["postedPrimaryOutcomeTables"][0]["statisticalComparisons"][0].update(reportedPValueLiteral="0.97"),
  lambda a,b:next(x for x in b["originalUniqueTrialEvidence"] if x["nct"]==NCT)["postedAdverseEventArmCountsAsReported"][0].update(seriousAffected=2),
])
def test_unsafe_data_eligible_predictions_or_source_drift_fail_closed(tmp_path,tamper):
    a,b,path=fixture(tmp_path)
    tamper(a,b)
    with pytest.raises(ValueError):reconcile(a,b,path)

def test_original_pdf_source_bytes_cannot_be_replaced(tmp_path):
    a,b,path=fixture(tmp_path)
    source=path/(NCT+"-SAP_001.pdf")
    source.write_bytes(source.read_bytes()+b"altered after receipt")
    with pytest.raises(ValueError,match="PDF_BYTES_DO_NOT_MATCH_R54_ORIGINAL"):
        reconcile(a,b,path)

def test_explicit_sap_section_11_change_must_be_present(tmp_path):
    a,b,path=fixture(tmp_path,without_sap_phrase=SAP[-1])
    # Bind the actual (altered) file's hash to both source packets, isolating the
    # missing phrase gate instead of failing earlier SHA integrity verification.
    changed=hashlib.sha256((path/(NCT+"-SAP_001.pdf")).read_bytes()).hexdigest()
    row=next(x for x in a["trialMethodsReview"] if x["nct"]==NCT)
    row["documents"][1]["sourceSha256"]=changed
    record=next(x for x in b["originalUniqueTrialEvidence"] if x["nct"]==NCT)
    record["sourceMethodsPageReferences"][1]["sha256"]=changed
    with pytest.raises(ValueError,match="EXPLICIT_CHANGE_NOT_FOUND"):
        reconcile(a,b,path)
