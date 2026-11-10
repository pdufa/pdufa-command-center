"""R54: original R51/R53 source crosswalk and no retrospective grade leakage."""
import hashlib
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest
from scripts.build_focus_scientific_review_queue_r54 import build

SHA="a"*64

def fixture(tmp_path):
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    ids=[x["nct"] for x in m["trialRows"]]
    picked=["NCT04544293"]+[n for n in ids if n!="NCT04544293"][:11]
    assert len(set(picked))==12
    by_nct={n:[] for n in ids}
    for app in m["applicationGroups"]:
        for n in app["ncts"]:by_nct[n].append(app["cycleId"])
    pdf_dir=tmp_path/"pdfs";pdf_dir.mkdir()
    docs=[]
    attachments={n:[] for n in ids}
    for i,nct in enumerate(picked):
        kinds=["Prot_SAP"] if i==11 else ["Prot","SAP"]
        for kind in kinds:
            filename=kind+"_001.pdf"
            data=("%PDF-1.4\nSource original "+nct+" "+kind+" clinical statistical review\n%%EOF").encode()
            archived=nct+"-"+filename
            (pdf_dir/archived).write_bytes(data)
            digest=hashlib.sha256(data).hexdigest()
            date="2024-04-24"
            docs.append({
              "nct":nct,"filename":filename,"archivedPdfFilename":archived,
              "sourceUrl":f"https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}",
              "currentRegistryDocumentDate":date,"hasProtocolFlag":kind in ("Prot","Prot_SAP"),
              "hasSapFlag":kind in ("SAP","Prot_SAP"),"sourceSha256":digest,"sourceBytes":len(data),
              "originalSAPFirstPublicDateVerified":False,
              "originalPreUnblindingLockedVersionVerified":False,
              "pdfResearch":{"pageCount":1,
                "keywordSourceExcerpts":[{"term":"primary endpoint","pdfPageOneBased":1,
                                          "sourceTextExcerpt":"Original statistical research review lead"}],
                "statisticalPrespecificationValidated":False,
                "regulatoryConclusionAuthorized":False,
                "sourceDocumentTextHumanReviewed":False
              }
            })
            attachments[nct].append({
              "filenameAsRegistry":filename,
              "documentDateAsRegistry":date,
              "hasProtocolFlagAsRegistry":kind in ("Prot","Prot_SAP"),
              "hasSapFlagAsRegistry":kind in ("SAP","Prot_SAP")
            })
    assert len(docs)==23
    e_trials=[{"nct":n,"currentRegistrySourceSha256":SHA,
       "currentProtocolSapAttachments":attachments[n],
       "postedPrimaryOutcomeCount":int(n in picked),
       "postedSafetyEventGroups":int(n in picked),
       "primary":[{"statisticalAnalyses":[{"pValueAsPublished":"0.05"}]}] if n in picked else [],
       "seriousEventTerms":[{"term":"source research entry"}] if n in picked else [],
       "otherEventTerms":[{"term":"source reported"}] if n in picked else [],
       "primaryTitleTimeframeConcordance":[],
       "currentRegistryResultsFirstPostDateAsReported":"2026-03-01"}
       for n in ids]
    r51={"schema":"MAIN_R51_FOCUS_23_SOURCE_REPORTED_EFFICACY_AND_SAFETY_DOSSIERS",
      "trialRosterCount":29,"applicationDossierCount":23,
      "validatedFDAForecasts":0,"productionOrClinicalLedgerWrites":False,
      "trialEvidence":e_trials,
      "applicationDossiers":[{"applicationCycleId":g["cycleId"],
        "exactNctIds":g["ncts"],"independentReviewerSignoff":False,
        "scientificGrade":None,"numericalFdaProbability":None}
        for g in m["applicationGroups"]]}
    r53={"schema":"MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH",
      "nctRosterCount":29,"applicationGroupCount":23,
      "currentRegistryDocumentEntries":23,"originalPdfBodiesRetrieved":23,
      "originalFirstPublicSAPDateVerified":0,
      "historicalRegisteredEndpointAmendmentChainVerified":0,
      "validatedFDAForecasts":0,"clinicalOrProductionWrites":False,
      "documentResearch":docs,
      "applicationResearch":[{"applicationCycleId":g["cycleId"],
         "exactNcts":g["ncts"],"officialFdaPrediction":"ABSTAIN",
         "statisticalReviewerSigned":False} for g in m["applicationGroups"]]}
    registry={"schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
      "nctCount":29,"applicationGroupCount":23,
      "records":[{"nct":n,"sourceResponseSha256":SHA,
         "applicationCycleIds":by_nct[n],
         "currentDocumentIndex":attachments[n]} for n in ids]}
    return m,r51,r53,registry,pdf_dir

def test_full_original_29_23_and_23_pdf_byte_verified_review_packets(tmp_path):
    m,e,d,index,pdf=fixture(tmp_path)
    r=build(m,e,d,index,pdf)
    assert (r["trialCount"],r["applicationCount"],r["protocolSapOriginalPdfFilesShaVerified"])==(29,23,23)
    assert len(r["applications"])==23
    assert r["crossRunCurrentRegistryVersionsFullyVerifiedEqual"] is True
    assert len({x["nct"] for a in r["applications"] for x in a["trialReviewPackets"]})==29
    assert r["applicationsWithCurrentSapPdf"]>0
    assert r["applicationsWithSourceReportedPrimaryResults"]>0
    assert r["validatedFDAOutcomePredictions"]==0
    assert r["approvalProbability"] is None
    assert r["historicalIndependentBacktests"]==0
    assert r["trainOrAutopredictAuthorized"] is False
    assert r["productionMutationAuthorized"] is False
    assert all(a["fdaForecastStatus"]=="ABSTAIN" and a["clinicalStatisticalReviewerSigned"] is False
               for a in r["applications"])
    assert all(x["crossRunRegistrySnapshotBytesIndependentlyMatched"] is True
               for a in r["applications"] for x in a["trialReviewPackets"])

def test_one_nct_may_support_two_original_cycles_and_not_duplicate_pdf_archives(tmp_path):
    m,e,d,index,pdf=fixture(tmp_path)
    result=build(m,e,d,index,pdf)
    nct="NCT02500381"
    assert sum(nct in x["exactNctIds"] for x in result["applications"])==2
    assert len(list(pdf.iterdir()))==23

@pytest.mark.parametrize("mutator",[
    lambda m,e,d,i,p:i["records"][0].update(sourceResponseSha256="b"*64),
    lambda m,e,d,i,p:e["trialEvidence"][0].update(currentRegistrySourceSha256="b"*64),
    lambda m,e,d,i,p:e["applicationDossiers"][0].update(independentReviewerSignoff=True),
    lambda m,e,d,i,p:d["applicationResearch"][0].update(officialFdaPrediction="APPROVAL"),
    lambda m,e,d,i,p:d.update(originalFirstPublicSAPDateVerified=1),
    lambda m,e,d,i,p:d["documentResearch"][0].update(originalPreUnblindingLockedVersionVerified=True),
    lambda m,e,d,i,p:d["documentResearch"][0].update(originalSAPFirstPublicDateVerified=True),
    lambda m,e,d,i,p:d["documentResearch"][0].update(sourceUrl="https://example.org/protocol.pdf"),
    lambda m,e,d,i,p:d["documentResearch"][0].update(sourceSha256="f"*64),
    lambda m,e,d,i,p:e["applicationDossiers"][0].update(numericalFdaProbability=.95),
    lambda m,e,d,i,p:d["documentResearch"].pop(),
    lambda m,e,d,i,p:i["records"][0].update(applicationCycleIds=["wrong"]),
    lambda m,e,d,i,p:e["trialEvidence"][0].update(currentProtocolSapAttachments=[]),
])
def test_forged_versions_incorrect_crosswalk_prediction_or_pdf_bytes_rejected(tmp_path,mutator):
    args=fixture(tmp_path)
    mutator(*args)
    with pytest.raises(ValueError):build(*args)

def test_actual_pdf_file_tampering_rejected_even_with_report_sha(tmp_path):
    args=fixture(tmp_path)
    filename=args[2]["documentResearch"][0]["archivedPdfFilename"]
    (args[4]/filename).write_bytes(b"%PDF-1.4 altered original")
    with pytest.raises(ValueError,match="PDF_ORIGINAL_BYTES_SHA_MISMATCH"):
        build(*args)

def test_missing_current_sap_attachments_do_not_mark_trial_failure(tmp_path):
    m,e,d,i,p=fixture(tmp_path)
    r=build(m,e,d,i,p)
    empty=[a for a in r["applications"] if not a["sourceArchiveHasSapPdf"]]
    assert empty
    for a in empty:
        assert a["fdaForecastStatus"]=="ABSTAIN"
        assert any("outside current registry" in q for q in a["clinicalEvidenceTaskList"])
        assert a["independentBenefitRiskConclusion"] is None
