"""MAIN R53: source-verified PDFs are research, not locked historical SAP evidence."""
from __future__ import annotations
import hashlib,json
from copy import deepcopy
import fitz,pytest
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest
from scripts.collect_focus_protocol_pdf_text_r53 import collect,safe_documents,inspect_pdf,public_fetch

def original_manifest_and_index():
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    ids={r["nct"]:[] for r in m["trialRows"]}
    for a in m["applicationGroups"]:
        for n in a["ncts"]:ids[n].append(a["cycleId"])
    rows=[]
    for nct in ids:
        entries=[]
        if nct=="NCT04544293":
            entries=[
              {"filenameAsRegistry":"Prot_000.pdf","documentDateAsRegistry":"2024-10-09",
               "hasProtocolFlagAsRegistry":True,"hasSapFlagAsRegistry":False},
              {"filenameAsRegistry":"SAP_001.pdf","documentDateAsRegistry":"2024-04-24",
               "hasProtocolFlagAsRegistry":False,"hasSapFlagAsRegistry":True}]
        if nct=="NCT04716231":
            entries=[{"filenameAsRegistry":"Prot_SAP_000.pdf",
              "documentDateAsRegistry":"2023-02-23",
              "hasProtocolFlagAsRegistry":True,"hasSapFlagAsRegistry":True}]
        rows.append({"nct":nct,"applicationCycleIds":ids[nct],
                     "currentDocumentIndex":entries})
    return m,{"schema":"MAIN_R46_PUBLIC_REGISTRY_PROTOCOL_SAP_INDEX",
           "nctCount":29,"applicationGroupCount":23,"records":rows}

def pdf(nct):
    doc=fitz.open()
    p=doc.new_page()
    p.insert_text((65,65),"Clinical study report protocol original",fontsize=12)
    p.insert_text((65,90),nct+" statistical analysis plan",fontsize=11)
    p.insert_text((65,115),"Primary endpoint Week 24 DLCO",fontsize=11)
    p.insert_text((65,140),"Multiplicity and hierarchical testing alpha 0.05",fontsize=11)
    p.insert_text((65,165),"Adverse event and safety population",fontsize=11)
    out=doc.tobytes()
    doc.close()
    assert len(out)>100
    return out

def fetch(url):
    nct=url.split("/")[-2]
    data=pdf(nct)
    return {"status":"FETCHED","contentType":"application/pdf",
        "sha256":hashlib.sha256(data).hexdigest(),"bytes":len(data)},data

def test_synthetic_pdf_has_exact_page_links_and_no_auto_statistical_grade(tmp_path):
    m,index=original_manifest_and_index()
    out=collect(m,index,fetch,tmp_path)
    assert out["nctRosterCount"]==29
    assert out["applicationGroupCount"]==23
    assert out["currentRegistryDocumentEntries"]==3
    assert out["originalPdfBodiesRetrieved"]==3
    assert out["currentProtocolPdfBodiesRetrieved"]==2
    assert out["currentSapPdfBodiesRetrieved"]==2
    assert len(out["applicationResearch"])==23
    assert out["independentScientificGrades"]==0
    assert out["validatedFDAForecasts"]==0
    assert out["measuredApprovalAccuracy"] is None
    assert out["clinicalOrProductionWrites"] is False
    assert out["officialFutureFDAOutcome"]=="ABSTAIN"
    for r in out["documentResearch"]:
        raw=(tmp_path/r["archivedPdfFilename"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r["sourceSha256"]
        assert r["pdfResearch"]["nctMentionedInInspectedPages"] is True
        assert r["pdfResearch"]["statisticalPrespecificationValidated"] is False
        assert r["pdfResearch"]["regulatoryConclusionAuthorized"] is False
        assert any(x["pdfPageOneBased"]==1 for x in r["pdfResearch"]["keywordSourceExcerpts"])

def test_shared_trial_links_and_current_metadata_not_first_public(tmp_path):
    m,index=original_manifest_and_index()
    out=collect(m,index,fetch,tmp_path)
    svra=next(x for x in out["applicationResearch"] if x["applicationCycleId"]=="svra-molgramostim")
    assert svra["exactNcts"]==["NCT04544293"]
    assert svra["originalPublicPdfBodiesVerified"]==2
    assert svra["originalPrespecifiedSAPFirstPublicBeforeTrialUnblinding"] is False
    assert svra["originalEndpointHierarchyAndMultiplicityAdjudicated"] is False
    assert svra["officialFdaPrediction"]=="ABSTAIN"
    capr=next(x for x in out["applicationResearch"] if x["applicationCycleId"]=="capr-deramiocel")
    assert capr["currentRegistryDocumentEntries"]==0

def test_unavailable_current_pdf_is_research_gap_not_trial_failure(tmp_path):
    m,index=original_manifest_and_index()
    def unavailable(url):return {"status":"HTTP_UNAVAILABLE","httpStatus":403},None
    out=collect(m,index,unavailable,tmp_path)
    assert out["originalPdfBodiesRetrieved"]==0
    assert out["sourceOutcomes"]=={"HTTP_UNAVAILABLE":3}
    assert not list(tmp_path.iterdir())
    assert all(x["officialFdaPrediction"]=="ABSTAIN" for x in out["applicationResearch"])

@pytest.mark.parametrize("modify",[
 lambda m,i:i.update(applicationGroupCount=22),
 lambda m,i:i["records"].pop(),
 lambda m,i:i["records"][0].update(nct="NCT99999999"),
 lambda m,i:i["records"][0].update(applicationCycleIds=["rogue-group"]),
 lambda m,i:next(r for r in i["records"] if r["nct"]=="NCT04544293")["currentDocumentIndex"][0].update(filenameAsRegistry="../../etc/passwd"),
 lambda m,i:next(r for r in i["records"] if r["nct"]=="NCT04544293")["currentDocumentIndex"][0].update(documentDateAsRegistry="unverified"),
 lambda m,i:next(r for r in i["records"] if r["nct"]=="NCT04544293")["currentDocumentIndex"][0].update(hasProtocolFlagAsRegistry=False,hasSapFlagAsRegistry=False),
])
def test_forged_public_doc_source_or_trial_membership_rejected(modify):
    m,index=original_manifest_and_index();modify(m,index)
    with pytest.raises(ValueError):safe_documents(m,index)

def test_original_pdf_bytes_sha_tamper_is_fatal(tmp_path):
    m,index=original_manifest_and_index()
    def tampered(url):
        record,data=fetch(url)
        return {**record,"sha256":"f"*64},data
    with pytest.raises(ValueError,match="SOURCE_SHA_MISMATCH"):
        collect(m,index,tampered,tmp_path)

def test_non_pdf_html_not_treated_as_protocol_source():
    with pytest.raises(ValueError,match="NON_PDF_ORIGINAL_SOURCE"):
        inspect_pdf(b"<html>statistical evidence</html>","NCT04544293")

@pytest.mark.parametrize("host",[
 "https://example.org/large-docs/93/NCT04544293/SAP_001.pdf",
 "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf?token=x",
 "http://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/SAP_001.pdf",
 "https://cdn.clinicaltrials.gov/large-docs/93/NCT04544293/../SAP_001.pdf"
])
def test_external_or_untrusted_attachment_url_cannot_be_fetched(host):
    with pytest.raises(ValueError,match="NON_CANONICAL"):
        public_fetch(host)
