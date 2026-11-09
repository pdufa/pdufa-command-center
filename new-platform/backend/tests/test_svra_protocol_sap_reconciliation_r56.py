"""R56 exact evidence page and SHA guards, research only; no statistical grade."""
from __future__ import annotations
import hashlib
from copy import deepcopy
import fitz,pytest
import scripts.reconcile_svra_original_protocol_sap_r56 as r56

def synthetic_pdf(title,phrase):
    doc=fitz.open()
    for i in range(3):
        page=doc.new_page()
        text=title if i==0 else phrase if i==1 else "Source review note"
        page.insert_text((40,60),text,fontsize=11)
    data=doc.tobytes();doc.close()
    return data

def inputs(monkeypatch):
    prot=synthetic_pdf("Protocol v10 09 October 2024",
        "Average of the two best efforts in DLCO")
    sap=synthetic_pdf("SAP v1 24APR2024",
        "Average of all acceptable efforts for DLCO")
    raw={r56.PROT:prot,r56.SAP:sap}
    exp={
      r56.PROT:{"sha256":hashlib.sha256(prot).hexdigest(),
        "date":"2024-10-09","pages":3,"type":"PROTOCOL_CURRENT_ATTACHED_VERSION_10"},
      r56.SAP:{"sha256":hashlib.sha256(sap).hexdigest(),
        "date":"2024-04-24","pages":3,"type":"SAP_CURRENT_ATTACHED_VERSION_1"}
    }
    monkeypatch.setattr(r56,"EXPECTED",exp)
    monkeypatch.setattr(r56,"ITEMS",(
       ("DLCO_MANEUVER_RULE","PRIMARY_ENDPOINT","RECONCILIATION_REQUIRED",
          ((r56.PROT,2,"average of the two best efforts"),
           (r56.SAP,2,"average of all acceptable efforts"))),
       ("VERSION_ORDER","DOCUMENT_CHRONOLOGY","DOCUMENT_DATES_NOT_FIRST_PUBLIC",
          ((r56.PROT,1,"09 October 2024"),(r56.SAP,1,"24APR2024")))
    ))
    r53={"schema":"MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH",
         "nctRosterCount":29,"applicationGroupCount":23,
         "originalPdfBodiesRetrieved":23,
         "validatedFDAForecasts":0,
         "documentResearch":[
            {"nct":r56.NCT,"archivedPdfFilename":fn,
             "sourceBytes":len(blob),"sourceSha256":exp[fn]["sha256"],
             "sourceUrl":"https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/"+fn,
             "currentRegistryDocumentDate":exp[fn]["date"],
             "retrievalStatus":"FETCHED",
             "pdfResearch":{"pageCount":3}}
            for fn,blob in raw.items()
         ]+[{"nct":"OTHER","archivedPdfFilename":"file_"+str(i)}
                for i in range(21)]}
    r54={"schema":"MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX",
         "canonicalTrials":29,"applicationGroups":23,
         "independentlyValidatedApplicationFdaPredictions":0,
         "trialMethodsReview":[{"nct":r56.NCT}]+[{"nct":"OTHER"} for i in range(28)],
         "applicationMethodsReview":[{"applicationCycleId":"group-"+str(i)} for i in range(23)]}
    r55={"schema":"MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS",
         "nctTrials":29,"applicationGroups":23,
         "sourceVerifiedCurrentProtocolSAPDocuments":23,
         "independentlyValidatedFDAApplicationForecasts":0,
         "clinicalOrProductionWrites":False,
         "originalUniqueTrialEvidence":[{"nct":"NCT"+str(i).zfill(8)} for i in range(29)],
         "currentSourceCasePackets":[
            {"applicationCycleId":r56.APP,"exactNcts":[r56.NCT]}
         ]+[{"applicationCycleId":"group-"+str(i),"exactNcts":[]}
            for i in range(22)]}
    return raw,r53,r54,r55

def test_source_page_verified_review_not_material_scientific_grade(monkeypatch):
    raw,r53,r54,r55=inputs(monkeypatch)
    r=r56.build(raw,r53,r54,r55)
    assert r["schema"]=="MAIN_R56_SAVARA_SOURCE_PAGE_VERSUS_SAP_RECONCILIATION_QUEUE"
    assert r["totalReviewItems"]==2
    assert r["explicitDiscrepancyReconciliationItems"]==1
    assert len(r["verifiedCurrentPublicDocuments"])==2
    assert r["pageAnchoredSourceReviewItems"][0]["sourceLeads"][0]["pdfPageOneBased"]==2
    assert r["pageAnchoredSourceReviewItems"][0]["clinicalMaterialityAdjudicated"] is False
    assert r["pageAnchoredSourceReviewItems"][1]["reviewClass"]=="DOCUMENT_DATES_NOT_FIRST_PUBLIC"
    assert r["independentlyValidatedApplicationFDAForecasts"]==0
    assert r["officialFDAOutcomePrediction"]=="ABSTAIN"
    assert r["approvalProbability"] is None
    assert r["historicalIndependentPredictionBacktests"]==0
    assert r["noModelTrainingClinicalOrProductionWrites"] is True

@pytest.mark.parametrize("tamper",[
    lambda raw,r53,r54,r55:r53.update(validatedFDAForecasts=1),
    lambda raw,r53,r54,r55:r53["documentResearch"].pop(),
    lambda raw,r53,r54,r55:r53["documentResearch"][0].update(sourceSha256="0"*64),
    lambda raw,r53,r54,r55:r53["documentResearch"][0].update(currentRegistryDocumentDate="2023-01-01"),
    lambda raw,r53,r54,r55:r53["documentResearch"][0].update(sourceUrl="https://attacker.example/protocol.pdf"),
    lambda raw,r53,r54,r55:r54.update(independentlyValidatedApplicationFdaPredictions=1),
    lambda raw,r53,r54,r55:r55.update(clinicalOrProductionWrites=True),
    lambda raw,r53,r54,r55:r55.update(independentlyValidatedFDAApplicationForecasts=1),
    lambda raw,r53,r54,r55:r55["currentSourceCasePackets"].pop(),
    lambda raw,r53,r54,r55:r55["currentSourceCasePackets"][0].update(exactNcts=["NCT12345678"])
])
def test_unverified_source_or_prediction_promotion_fails_closed(monkeypatch,tamper):
    raw,r53,r54,r55=inputs(monkeypatch)
    tamper(raw,r53,r54,r55)
    with pytest.raises(ValueError):
        r56.build(raw,r53,r54,r55)

def test_pdf_byte_tampering_is_fatal(monkeypatch):
    raw,r53,r54,r55=inputs(monkeypatch)
    raw[r56.SAP]=raw[r56.SAP]+b"unregistered edit"
    with pytest.raises(ValueError,match="SAVARA_EXACT_SOURCE_BYTES_OR_DATE_RECEIPT_MISMATCH"):
        r56.build(raw,r53,r54,r55)

def test_pdf_original_page_phrase_must_actually_exist(monkeypatch):
    raw,r53,r54,r55=inputs(monkeypatch)
    monkeypatch.setattr(r56,"ITEMS",(
      ("ALTERED","PRIMARY_ENDPOINT","RECONCILIATION_REQUIRED",
        ((r56.PROT,2,"this evidence cannot be invented"),)),
    ))
    with pytest.raises(ValueError,match="SOURCE_PHRASE_NO_LONGER_ON_EXPECTED_PAGE"):
        r56.build(raw,r53,r54,r55)

def test_original_real_source_expectations_are_static_canonical_sha256(monkeypatch):
    # A source document needs explicit original byte/hash validation; pinning
    # must cover the full PDF, not a fragment of its printed document header.
    assert r56.NCT=="NCT04544293"
    assert r56.APP=="svra-molgramostim"
    assert len(r56.ITEMS)==10
    assert len({x[0] for x in r56.ITEMS})==10
    assert sum(x[2]=="RECONCILIATION_REQUIRED" for x in r56.ITEMS)==6
    assert r56.EXPECTED[r56.PROT]["pages"]==134
    assert r56.EXPECTED[r56.SAP]["pages"]==89
    assert r56.EXPECTED[r56.PROT]["sha256"]=="0748f6e524971b4612eaaf509b61cf1569f0393a3475a6ee172789fa71c0c849"
    assert r56.EXPECTED[r56.SAP]["sha256"]=="2f3494c191c2038322e0047b040a03ef5f99e1b02be2fb373f477e2930855888"
