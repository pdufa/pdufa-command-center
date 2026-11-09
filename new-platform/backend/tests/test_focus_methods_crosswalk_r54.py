"""R54: the page-cited methods map is reproducible evidence, not a rating."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import fitz,pytest
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest
from scripts.build_focus_methods_crosswalk_r54 import build,DOMAINS

FILES={
 "NCT03697109":["Prot_002.pdf","SAP_001.pdf"],
 "NCT04308590":["Prot_000.pdf","SAP_001.pdf"],
 "NCT04544293":["Prot_000.pdf","SAP_001.pdf"],
 "NCT04576949":["Prot_000.pdf","SAP_001.pdf"],
 "NCT04716231":["Prot_SAP_000.pdf"],
 "NCT05206370":["Prot_000.pdf","SAP_001.pdf"],
 "NCT05507203":["Prot_000.pdf","SAP_001.pdf"],
 "NCT05507216":["Prot_000.pdf","SAP_001.pdf"],
 "NCT05767346":["Prot_000.pdf","SAP_001.pdf"],
 "NCT05811247":["Prot_000.pdf","SAP_001.pdf"],
 "NCT05813275":["Prot_000.pdf","SAP_001.pdf"],
 "NCT06331299":["Prot_000.pdf","SAP_001.pdf"]
}
MEASURE="Change from baseline in DLCO at Week 24"

def make_pdf(nct,visible=True):
    d=fitz.open();page=d.new_page()
    lines=[
       "Original public NCT "+nct,
       "Primary endpoint: "+MEASURE if visible else "Original PDF has no primary-outcome phrase",
       "Full Analysis Set and per-protocol set; estimand review",
       "Mixed model and repeated measurements analysis",
       "Multiplicity control and type I error alpha splitting",
       "Missing data with multiple imputation",
       "Sensitivity analyses, multiple treatment strategies",
       "Serious adverse event and safety population",
       "Protocol amendment and summary of changes"
    ]
    for i,line in enumerate(lines):page.insert_text((40,55+i*24),line,fontsize=10)
    result=d.tobytes();d.close()
    return result

def fixture(tmp_path):
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    pdf=tmp_path/"pdf";reg=tmp_path/"registry"
    pdf.mkdir();reg.mkdir()
    ids={n["nct"]:[] for n in m["trialRows"]}
    for g in m["applicationGroups"]:
        for n in g["ncts"]:ids[n].append(g["cycleId"])
    rows=[]
    for nct,names in FILES.items():
        original={"protocolSection":{
           "identificationModule":{"nctId":nct},
           "outcomesModule":{"primaryOutcomes":[{"measure":MEASURE,"timeFrame":"Week 24"}]}
        }}
        (reg/(nct+".json")).write_text(json.dumps(original))
        for filename in names:
            data=make_pdf(nct)
            pref=nct+"-"+filename
            (pdf/pref).write_bytes(data)
            combined=filename.startswith("Prot_SAP_")
            p=filename.startswith("Prot_") or combined
            s=filename.startswith("SAP_") or combined
            date=("2024-04-24" if nct=="NCT04544293" and s else
                  "2024-10-09" if nct=="NCT04544293" and p else "2025-07-15")
            rows.append({
              "nct":nct,"filename":filename,"archivedPdfFilename":pref,
              "sourceUrl":"https://cdn.clinicaltrials.gov/large-docs/"+nct[-2:]+"/"+nct+"/"+filename,
              "sourceSha256":hashlib.sha256(data).hexdigest(),"sourceBytes":len(data),
              "retrievalStatus":"FETCHED","pdfResearch":{"pageCount":1},
              "applicationCycleIds":ids[nct],
              "hasProtocolFlag":p,"hasSapFlag":s,
              "currentRegistryDocumentDate":date
            })
    assert len(rows)==23
    report={
      "schema":"MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH",
      "nctRosterCount":29,"applicationGroupCount":23,
      "currentRegistryDocumentEntries":23,
      "originalPdfBodiesRetrieved":23,"trialNctsWithDocumentEntries":12,
      "independentScientificGrades":0,"validatedFDAForecasts":0,
      "clinicalOrProductionWrites":False,"documentResearch":rows
    }
    return m,report,pdf,reg

def test_23_original_files_map_to_29_trials_23_apps_and_eight_nonjudgmental_dimensions(tmp_path):
    m,report,pdf,reg=fixture(tmp_path)
    out=build(m,report,pdf,reg)
    assert out["canonicalTrials"]==29
    assert out["applicationGroups"]==23
    assert out["currentPdfDocumentsSourceVerified"]==23
    assert out["trialsWithCurrentSourcePdfDocuments"]==12
    assert out["trialsWithoutCurrentAttachedProtocolSap"]==17
    assert len(out["eightMethodsReviewDomains"])==8
    assert len(out["applicationMethodsReview"])==23
    assert len(out["trialMethodsReview"])==29
    assert out["historicalLockedSapVersionsIndependentlyVerified"]==0
    assert out["independentlySignedClinicalMethodGrades"]==0
    assert out["independentlyValidatedApplicationFdaPredictions"]==0
    assert out["measuredFDAApprovalAccuracy"] is None
    assert out["clinicalOrProductionWrites"] is False
    svra=next(x for x in out["trialMethodsReview"] if x["nct"]=="NCT04544293")
    assert svra["sourceDocumentCount"]==2
    assert ("CURRENT_SAP_DOCUMENT_DATE_EARLIER_THAN_LATEST_ATTACHED_PROTOCOL_DATE_AMENDMENT_REVIEW"
        in svra["reviewFlags"])
    sap=next(x for x in svra["documents"] if x["sapFlagFromCurrentRegistry"])
    for domain in DOMAINS:
        entry=sap["machineTextEvidence"]["eightSourceReviewDomains"][domain]
        assert entry["sourceState"]=="PAGE_LINKED_TERMS_FOUND_REVIEW_REQUIRED"
        assert entry["pageLinkedSourceLeads"][0]["pdfPageOneBased"]==1
        assert entry["pageLinkedSourceLeads"][0]["indexOrIntroPagePossibility"] is True
    assert sap["machineTextEvidence"]["currentRegisteredPrimaryEndpointLiteralMatches"][0]["sourceStatus"]=="LITERAL_MEASURE_TEXT_FOUND"
    assert sap["machineTextEvidence"]["historicalProspectiveSAPLockVerified"] is False
    assert sap["regulatorOutcomePrediction"]=="ABSTAIN"

def test_no_current_attached_document_does_not_mean_fda_failure(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    out=build(m,r,pdf,reg)
    capr=next(x for x in out["applicationMethodsReview"] if x["applicationCycleId"]=="capr-deramiocel")
    assert capr["availableCurrentPdfDocuments"]==0
    assert capr["officialFDAPrediction"]=="ABSTAIN"
    assert capr["fdaApprovalProbability"] is None
    t=next(x for x in out["trialMethodsReview"] if x["nct"]=="NCT05126758")
    assert "NO_CURRENT_REGISTRY_ATTACHED_PROTOCOL_SAP_OTHER_SOURCES_POSSIBLE" in t["reviewFlags"]

def test_combined_original_and_final_document_requires_independent_amendment_review(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    out=build(m,r,pdf,reg)
    t=next(x for x in out["trialMethodsReview"] if x["nct"]=="NCT04716231")
    assert t["sourceDocumentCount"]==1
    assert "COMBINED_DOCUMENT_MAY_CONTAIN_ORIGINAL_AND_FINAL_VERSIONS_REVIEW_REQUIRED" in t["reviewFlags"]

def test_no_literal_primary_measure_hit_is_not_evidence_of_endpoint_change(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    row=next(x for x in r["documentResearch"] if x["nct"]=="NCT04544293")
    data=make_pdf("NCT04544293",False)
    (pdf/row["archivedPdfFilename"]).write_bytes(data)
    row["sourceSha256"]=hashlib.sha256(data).hexdigest()
    row["sourceBytes"]=len(data)
    out=build(m,r,pdf,reg)
    t=next(x for x in out["trialMethodsReview"] if x["nct"]=="NCT04544293")
    selected=next(x for x in t["documents"] if x["filename"]==row["filename"])
    assert selected["machineTextEvidence"]["currentRegisteredPrimaryEndpointLiteralMatches"][0]["sourceStatus"].startswith("NO_LITERAL")
    assert selected["machineTextEvidence"]["clinicalMethodCompletenessVerified"] is False

@pytest.mark.parametrize("mutate",[
  lambda r:r.update(independentScientificGrades=1),
  lambda r:r.update(validatedFDAForecasts=1),
  lambda r:r.update(originalPdfBodiesRetrieved=22),
  lambda r:r["documentResearch"][0].update(sourceSha256="0"*64),
  lambda r:r["documentResearch"][0].update(archivedPdfFilename="../../bad.pdf"),
  lambda r:r["documentResearch"][0].update(nct="NCT99999999"),
  lambda r:r["documentResearch"][0].update(retrievalStatus="FORGED"),
  lambda r:r["documentResearch"][0].update(applicationCycleIds=["bad"]),
  lambda r:r["documentResearch"][1].update(archivedPdfFilename=r["documentResearch"][0]["archivedPdfFilename"]),
])
def test_exact_source_identity_provenance_and_false_grade_tamper_refused(tmp_path,mutate):
    m,r,pdf,reg=fixture(tmp_path)
    mutate(r)
    with pytest.raises(ValueError):build(m,r,pdf,reg)

def test_changed_original_byte_hash_rejected_even_if_pdf_parses(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    entry=r["documentResearch"][0]
    (pdf/entry["archivedPdfFilename"]).write_bytes(make_pdf(entry["nct"],False))
    with pytest.raises(ValueError,match="ORIGINAL_PUBLIC_PDF_HASH_MISMATCH"):
        build(m,r,pdf,reg)

def test_wrong_nct_registry_bytes_refused(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    (reg/"NCT04544293.json").write_text(json.dumps(
        {"protocolSection":{"identificationModule":{"nctId":"NCT99999999"}}}))
    with pytest.raises(ValueError,match="ORIGINAL_REGISTRY_NCT_MISMATCH"):
        build(m,r,pdf,reg)

def test_double_linked_trial_is_one_trial_record_not_double_counted(tmp_path):
    m,r,pdf,reg=fixture(tmp_path)
    out=build(m,r,pdf,reg)
    assert sum("NCT02500381" in x["exactNcts"] for x in out["applicationMethodsReview"])==2
    assert sum(x["nct"]=="NCT02500381" for x in out["trialMethodsReview"])==1
