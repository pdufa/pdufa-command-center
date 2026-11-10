"""R70 PubMed primary-source XML is article metadata, NOT a clinical grade."""
from __future__ import annotations

import copy
import os
from pathlib import Path
from xml.sax.saxutils import escape
import pytest
from scripts.build_focus_pubmed_article_records_r70 import (
  R69_SHA,EXPECTED_CASES,read_original,parse_pubmed_xml,build_report,
  article_scope_flags
)

PMID_TO_NCT={pmid:nct for nct,pmids in EXPECTED_CASES.items() for pmid in pmids}


def mock_xml(*,missing=None,forgery=None,dtd=False):
  articles=[]
  for pmid,nct in PMID_TO_NCT.items():
    if pmid==missing:continue
    title=("Phase II dose-finding open-label study" if pmid=="42848980"
           else "Phase 3 primary endpoint clinical trial report")
    if pmid=="40098309":
      title="Reference percentiles in healthy children"
    ncts=[nct]
    if pmid=="40098309":ncts=["NCT03863197"]
    if pmid==forgery:ncts=["NCT00000000"]
    abstract=(f"Trial registration {nct}; phase 3 trial primary endpoint."
      if pmid not in ("40098309","34105177","42848980") else
      "Background discussion about prior studies and muscle outcomes.")
    bank="".join(f"<AccessionNumber>{n}</AccessionNumber>" for n in ncts)
    articles.append(f"""<PubmedArticle>
       <MedlineCitation><PMID>{pmid}</PMID><Article>
         <Journal><JournalIssue><PubDate><Year>2026</Year><Month>Oct</Month></PubDate></JournalIssue>
         <Title>Journal Test</Title></Journal>
         <ArticleTitle>{escape(title)}</ArticleTitle>
         <Abstract><AbstractText Label="METHODS">{escape(abstract)}</AbstractText></Abstract>
         <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
         </Article><DataBankList><DataBank><DataBankName>ClinicalTrials.gov</DataBankName>
         <AccessionNumberList>{bank}</AccessionNumberList></DataBank>
         </DataBankList></MedlineCitation>
         <PubmedData><ArticleIdList><ArticleId IdType="doi">10.5555/{pmid}</ArticleId></ArticleIdList></PubmedData>
         </PubmedArticle>""")
  head='<?xml version="1.0" encoding="UTF-8"?>'
  if dtd:
    head+='\n<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2026//EN" "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_260101.dtd">'
  return (head+"\n<PubmedArticleSet>"+"".join(articles)+"</PubmedArticleSet>").encode()


def test_11_strict_source_records_and_no_clinical_or_regulatory_grade():
  records=parse_pubmed_xml(mock_xml(),PMID_TO_NCT,
    source_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi")
  assert len(records)==11
  assert len({r["pmid"] for r in records})==11
  assert all(r["clinicalGrade"] is None and
    r["scientificReviewerSigned"] is False and
    r["pivotalPhase3PrimaryResultsIndependentlyVerified"] is False and
    r["fullTextIndependentlyRead"] is False and
    r["preUnblindingProtocolSapVersionVerified"] is False and
    r["fdaApprovalOrCrlPrediction"]=="ABSTAIN" for r in records)
  fake_background=next(r for r in records if r["pmid"]=="40098309")
  assert fake_background["exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract"] is False
  assert fake_background["nctIdentifiersFromDatabank"]==["NCT03863197"]
  exact=next(r for r in records if r["pmid"]=="42526472")
  assert exact["exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract"] is True
  phase2=next(r for r in records if r["pmid"]=="42848980")
  assert "PHASE_1_OR_2_TERM" in phase2["literalSourceTextScopeFlags"]
  report=build_report(R69_SHA,records,"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi")
  assert report["articleMetadataRecordsRetrieved"]==11
  assert report["articlesWithIndependentlyAdjudicatedPivotalOutcomes"]==0
  assert report["qualifiedReviewerSignoffs"]==0
  assert report["scoredScientificMethods"]==0
  assert report["validatedFutureFdaApplicationPredictions"]==0
  assert report["officialFutureFDAOutcome"]=="ABSTAIN"
  assert report["measuredHistoricalForecastAccuracy"] is None
  assert report["modelTrainingOrProductionWrites"] is False
  assert report["originalArticleFullTextsRetrieved"]==0


def test_official_nlm_public_dtd_is_stripped_without_fetching_external_entities():
  r=parse_pubmed_xml(mock_xml(dtd=True),PMID_TO_NCT,source_url="test")
  assert len(r)==11


@pytest.mark.parametrize("xml",[
 lambda:mock_xml(missing="42526472"),
 lambda:mock_xml().replace(b"<PMID>42526472</PMID>",b"<PMID>40098309</PMID>"),
 lambda:mock_xml().replace(b"<PubmedArticleSet>",b"<other>"),
 lambda:mock_xml().replace(b"<ArticleTitle>",b"<!ENTITY x SYSTEM 'file:///etc/passwd'><ArticleTitle>",1),
 lambda:mock_xml().replace(b"<PubmedArticleSet>",b'<!DOCTYPE PubmedArticleSet [ <!ENTITY x "ab"> ]><PubmedArticleSet>',1),
])
def test_partial_source_id_injection_duplicate_and_unknown_shapes_fail_closed(xml):
  with pytest.raises((ValueError,TypeError)):
    parse_pubmed_xml(xml(),PMID_TO_NCT,source_url="test")


def test_absent_explicit_trial_id_remains_candidate_not_falsely_pivotal():
  r=parse_pubmed_xml(mock_xml(forgery="42526472"),PMID_TO_NCT,source_url="test")
  capr=next(x for x in r if x["pmid"]=="42526472")
  assert capr["exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract"] is True
  # True comes from the literal abstract, not proof of this paper's study;
  # a fabricated databank ID never earns an independent clinical grade.
  assert capr["nctIdentifiersFromDatabank"]==["NCT00000000"]
  assert capr["scientificReviewerSigned"] is False
  assert capr["pivotalPhase3PrimaryResultsIndependentlyVerified"] is False


def test_scope_terms_are_only_literal_hypotheses_not_fda_prognoses():
  flags=article_scope_flags("Phase 2/3 dose-finding trial",
    "Phase III trial: primary outcome and exploratory secondary endpoint.")
  assert "PHASE_1_OR_2_TERM" in flags
  assert "PHASE_3_TERM" in flags
  assert "PRIMARY_ENDPOINT_TERM" in flags
  assert "EXPLORATORY_OR_SECONDARY_TERM" in flags


def test_exact_original_r69_input_sha_and_no_signoff_env_mounted():
  source=os.environ.get("R70_R69")
  assert source,"R70 must restore immutable R69 source before tests"
  doc,mapping=read_original(Path(source))
  assert doc["registryListedUnverifiedPubmedReferences"]==11
  assert mapping==PMID_TO_NCT
  assert len(mapping)==11
