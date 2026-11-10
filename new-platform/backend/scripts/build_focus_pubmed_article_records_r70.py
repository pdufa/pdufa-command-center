#!/usr/bin/env python3
"""MAIN R70: retrieve and archive the 11 exact PubMed article METADATA+ABSTRACT records
listed by the already SHA-locked R69 original registry source.

Important scientific limitations: PubMed may link an NCT to a related
background, methods/protocol, earlier-phase or exploratory article. Merely
mentioning an NCT, primary endpoint, or statistical significance DOES NOT
establish that the publication represents an exact pivotal Phase 3 primary
outcome or that it meets a prospectively locked statistical analysis plan.
PubMed XML is not a verified full-text article or a clinical reviewer signoff.
No historical FDA outcomes, production, RAAS or model training is read/written.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path

R69_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77"
R69_SCHEMA="MAIN_R69_ORIGINAL_REGISTRY_PUBMED_REFERENCE_LEAD_RECOVERY"
SCHEMA="MAIN_R70_ORIGINAL_PUBMED_XML_METADATA_ABSTRACT_EVIDENCE_LEADS"
NCT_RE=re.compile(r"NCT[0-9]{8}\b",re.I)
PMID_RE=re.compile(r"[1-9][0-9]{5,9}\Z")
MAX_SOURCE_BYTES=2_000_000
EUTILS="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids}&retmode=xml"
EXPECTED_CASES={
 "NCT02500381":("40098309","34105177"),
 "NCT04871282":("42848980",),
 "NCT05126758":("42526472",),
 "NCT05662241":("42233621","41840328"),
 "NCT06081894":("42667274","42663312","42663111"),
 "NCT06153693":("40587141",),
 "NCT06343779":("42849489",),
}


def require(test,code):
    if not test:raise ValueError(code)


def read_original(path:Path):
    require(path.is_file() and not path.is_symlink()
            and 100<path.stat().st_size<1_200_000,"ORIGINAL_R69_REPORT_UNAVAILABLE")
    b=path.read_bytes()
    require(hashlib.sha256(b).hexdigest()==R69_SHA,
            "UNPINNED_R69_ORIGINAL_REPORT_SHA")
    out=json.loads(b)
    require(type(out) is dict and out.get("schema")==R69_SCHEMA
            and out.get("canonicalUniqueNcts")==29
            and out.get("provisionalApplicationCycles")==23
            and out.get("originalRegistryNoCurrentPrimaryTrials")==17
            and out.get("missingPrimaryTrialsWithPubmedReferenceLeads")==7
            and out.get("missingPrimaryTrialsWithoutPubmedReferenceLeads")==10
            and out.get("registryListedUnverifiedPubmedReferences")==11
            and out.get("independentlyVerifiedArticlesReportingExactTrialPrimary")==0
            and out.get("independentlyQualifiedReviewerAssessments")==0
            and out.get("validatedFutureFDAForecasts")==0
            and out.get("FDAOutcome")=="ABSTAIN"
            and out.get("measuredPredictionAccuracy") is None
            and out.get("historicalBacktestDataInspected") is False
            and out.get("modelTrainingOrProductionWrites") is False,
            "R69_REQUIRED_SOURCE_AND_SCIENTIFIC_GATES_FAILED")
    cases=out.get("missingPrimaryLiteratureReviewQueue")
    require(type(cases) is list and len(cases)==17
            and len({c["nct"] for c in cases})==17,
            "R69_EXACT_17_NCT_LIST_REQUIRED")
    lead_map={}
    for case in cases:
        nct=case["nct"]
        require(re.fullmatch(r"NCT[0-9]{8}",nct)
                and case.get("currentRegistryPrimaryTables")==0
                and case.get("officialFdaForecast")=="ABSTAIN"
                and case.get("scientificMethodGrade") is None,
                "FALSE_ORIGINAL_REGISTRY_EFFICACY_CLAIM")
        leads=case["registryDerivedPubmedReferenceLeads"]
        require(type(leads) is list and len(leads)<=12,
                "R69_SOURCE_LEAD_FORMAT")
        for lead in leads:
            pmid=lead["pmid"]
            require(type(pmid) is str and PMID_RE.fullmatch(pmid)
                    and lead.get("pubmedUrl")=="https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/"
                    and lead.get("registryReferenceType")=="DERIVED"
                    and lead.get("articleContentIndependentlyInspected") is False
                    and lead.get("exactNctMentionInArticleVerified") is False
                    and lead.get("paperReportsPivotalPrimaryOutcomeVerified") is False
                    and lead.get("independentQualifiedPublicationReviewSigned") is False,
                    "R69_ORIGINAL_UNREVIEWED_LEAD_GATES")
            require(pmid not in lead_map,"SAME_PMID_REFERENCED_BY_MULTIPLE_FOCUS_NCT")
            lead_map[pmid]=nct
    require(len(lead_map)==11
            and {n:tuple(p for p,linked in lead_map.items() if linked==n)
                 for n in EXPECTED_CASES}==EXPECTED_CASES,
            "R69_EXACT_ORIGINAL_REFERENCE_MEMBERSHIP_CHANGED")
    return out,lead_map


def fetch_pubmed_xml(pmids: list[str],*,attempts:int=3,nap=time.sleep):
    require(len(pmids)==11 and len(set(pmids))==11
            and all(PMID_RE.fullmatch(p) for p in pmids),
            "UNSAFE_PUBMED_SOURCE_QUERY")
    url=EUTILS.format(ids=",".join(pmids))
    headers={
      "User-Agent":"PDUFA-FOCUS-R70-original-pubmed-article-source-research/1.0",
      "Accept":"application/xml"
    }
    request=urllib.request.Request(url,headers=headers,method="GET")
    context=ssl.create_default_context()
    last=None
    for i in range(attempts):
        try:
            with urllib.request.urlopen(request,timeout=30,context=context) as res:
                require(res.url.startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"),
                        "PUBMED_SOURCE_HOST_REDIRECT_DISALLOWED")
                require(res.status==200,"PUBMED_FETCH_NON200")
                data=res.read(MAX_SOURCE_BYTES+1)
                require(len(data)<MAX_SOURCE_BYTES and data.startswith(b"<?xml"),
                        "PUBMED_XML_EMPTY_OR_OVERSIZED_OR_NONXML")
                return data,url
        except (OSError,urllib.error.HTTPError,TimeoutError) as err:
            last=err
            if i+1<attempts:nap(2*(i+1))
    raise RuntimeError("PUBMED_METADATA_SOURCE_UNAVAILABLE_NO_RESULT_INFERRED") from last


def text(node):
    if node is None:return ""
    return " ".join(" ".join(node.itertext()).split())


def article_scope_flags(title,abstract):
    """Only observations of literal source words. NEVER grade trial outcome."""
    lower=(" ".join([title,abstract])).casefold()
    scope=[]
    for name,patterns in (
      ("PHASE_1_OR_2_TERM",("phase i/ii","phase 1/2","phase 1-2","phase ii",
                           "phase 2","dose-finding","dose titration","dose-titration")),
      ("PHASE_3_TERM",("phase iii","phase 3","phase-3","phase iii trial")),
      ("PROTOCOL_OR_METHODS_TERM",("protocol for","study protocol","design and rationale")),
      ("PRIMARY_ENDPOINT_TERM",("primary endpoint","primary end point","primary outcome")),
      ("EXPLORATORY_OR_SECONDARY_TERM",("exploratory","secondary endpoint",
                                       "secondary end point","prespecified exploratory")),
    ):
        if any(term in lower for term in patterns):scope.append(name)
    return scope


def parse_pubmed_xml(data:bytes,mapping:dict[str,str],*,source_url:str):
    require(type(data) is bytes and 100<len(data)<MAX_SOURCE_BYTES
            and data.lstrip().startswith(b"<?xml") and
            b"<!DOCTYPE" not in data and b"<!ENTITY" not in data,
            "UNTRUSTED_PUBMED_SOURCE_XML")
    try:root=ET.fromstring(data)
    except ET.ParseError as err:raise ValueError("PUBMED_SOURCE_XML_PARSE_FAILED") from err
    require(root.tag=="PubmedArticleSet","PUBMED_RESPONSE_NOT_ARTICLE_SET")
    articles=root.findall("./PubmedArticle")
    require(len(articles)==11,"PUBMED_FETCH_PARTIAL_OR_EXTRA_RECORDS")
    done=set()
    rows=[]
    for a in articles:
        med=a.find("./MedlineCitation")
        art=med.find("./Article") if med is not None else None
        pmid=text(med.find("./PMID")) if med is not None else ""
        require(PMID_RE.fullmatch(pmid) and pmid in mapping and pmid not in done
                and art is not None,"PUBMED_MALFORMED_DUPLICATE_OR_UNLISTED_ID")
        done.add(pmid)
        nct=mapping[pmid]
        title=text(art.find("./ArticleTitle"))
        journal=text(art.find("./Journal/Title"))
        abstract=text(art.find("./Abstract"))
        require(5<len(title)<700 and 2<len(journal)<220 and len(abstract)<30_000,
                "PUBMED_ARTICLE_METADATA_UNTRUSTED")
        ids=a.findall("./PubmedData/ArticleIdList/ArticleId")
        doi=next((text(x) for x in ids if x.attrib.get("IdType")=="doi"),None)
        if doi is not None:
            require(len(doi)<180 and doi.startswith("10."),"PUBMED_DOI_UNTRUSTED")
        ncts_in_accessions=set()
        for bank in med.findall("./DataBankList/DataBank"):
            if text(bank.find("./DataBankName")).lower()=="clinicaltrials.gov":
                for accession in bank.findall("./AccessionNumberList/AccessionNumber"):
                    ncts_in_accessions.update(x.upper() for x in NCT_RE.findall(text(accession)))
        ncts_in_abstract=set(x.upper() for x in NCT_RE.findall(abstract))
        ncts_in_title=set(x.upper() for x in NCT_RE.findall(title))
        reported=sorted(ncts_in_accessions|ncts_in_abstract|ncts_in_title)
        types=[text(p) for p in art.findall("./PublicationTypeList/PublicationType")]
        types=[x for x in types if 0<len(x)<130]
        pubdate=text(art.find("./Journal/JournalIssue/PubDate"))
        electronic=art.find("./ArticleDate")
        electronic_date="-".join(text(electronic.find("./"+tag)) for tag in ("Year","Month","Day")) if electronic is not None else None
        if electronic_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",electronic_date):
            electronic_date=None
        require(len(pubdate)<100 and len(types)<40,"PUBMED_DATE_TYPE_SOURCE_INVALID")
        scope=article_scope_flags(title,abstract)
        exact=nct in reported
        rows.append({
          "nct":nct,"pmid":pmid,
          "pubmedUrl":"https://pubmed.ncbi.nlm.nih.gov/"+pmid+"/",
          "sourceXmlSha256":hashlib.sha256(data).hexdigest(),
          "articleTitleExactlyAsPubmed":title,
          "journalExactlyAsPubmed":journal,
          "sourceJournalPubDateText":pubdate,
          "sourceElectronicPublicationDate":electronic_date,
          "doiAsPubmed":doi,
          "pubmedPublicationTypes":types,
          "sourceAbstractAvailable":bool(abstract),
          "sourceAbstractSha256":hashlib.sha256(abstract.encode()).hexdigest() if abstract else None,
          "nctIdentifiersFromDatabank":sorted(ncts_in_accessions),
          "nctIdentifiersFromArticleTitle":sorted(ncts_in_title),
          "nctIdentifiersFromAbstract":sorted(ncts_in_abstract),
          "exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract":exact,
          "literalSourceTextScopeFlags":scope,
          "sourceEvidentiaryClassification":"EXACT_NCT_ARTICLE_METADATA_LEAD_REQUIRES_SCIENTIFIC_REVIEW"
             if exact else "NO_EXACT_NCT_IDENTIFIER_IN_RETRIEVED_PUBMED_METADATA_ABSTRACT",
          "pivotalPhase3PrimaryResultsIndependentlyVerified":False,
          "trialPhaseMatchIndependentlyVerified":False,
          "fullTextIndependentlyRead":False,
          "preUnblindingProtocolSapVersionVerified":False,
          "statisticalEndpointsAdjudicated":False,
          "scientificReviewerSigned":False,
          "clinicalGrade":None,
          "fdaApprovalOrCrlPrediction":"ABSTAIN",
        })
    require(done==set(mapping),"PUBMED_SOURCE_SET_INCOMPLETE")
    return sorted(rows,key=lambda x:(x["nct"],x["pmid"]))


def build_report(r69_sha,rows,source_url):
    require(r69_sha==R69_SHA and len(rows)==11 and len({r["pmid"] for r in rows})==11,
            "PUBMED_ARTICLE_REPORT_SOURCE_INCOMPLETE")
    present=sum(bool(r["exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract"]) for r in rows)
    no_match=11-present
    return {
      "schema":SCHEMA,
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "inputOriginalR69Sha256":r69_sha,
      "originalPubmedEutilsSourceUrl":source_url,
      "originalPubmedXmlSha256":rows[0]["sourceXmlSha256"],
      "focusExactNcts":29,"provisionalFDAApplicationGroups":23,
      "originalRegistryNctsWithoutCurrentPrimary":17,
      "registryDerivedPubmedCitationLeads":11,
      "articleMetadataRecordsRetrieved":11,
      "exactNctIdentifiersFoundInRetrievedMetadataOrAbstract":present,
      "noExactNctIdentifierFoundInRetrievedMetadataOrAbstract":no_match,
      "articlesWithIndependentlyAdjudicatedPivotalOutcomes":0,
      "qualifiedReviewerSignoffs":0,
      "scoredScientificMethods":0,
      "validatedFutureFdaApplicationPredictions":0,
      "measuredHistoricalForecastAccuracy":None,
      "officialFutureFDAOutcome":"ABSTAIN",
      "modelTrainingOrProductionWrites":False,
      "originalArticleFullTextsRetrieved":0,
      "pubmedAbstractsAreNotFullPublicationAnalysis":True,
      "machineNctIdentifierMatchDoesNotEstablishClinicalGrade":True,
      "articleResearchLeads":rows
    }


def summary(report):
    lines=[
      "# MAIN R70 — PubMed original article metadata and abstract research audit",
      "",
      "PubMed metadata/abstract is not the full paper, original signed SAP,"
      " independent human statistical review or a validated FDA forecast.",
      "",
      f'- Original PubMed article metadata rows: **{report["articleMetadataRecordsRetrieved"]}/11**.',
      f'- Exact NCT literal identifier found in PubMed metadata/abstract: **{report["exactNctIdentifiersFoundInRetrievedMetadataOrAbstract"]}/11**.',
      f'- Exact NCT identifier not found in this metadata/abstract: **{report["noExactNctIdentifierFoundInRetrievedMetadataOrAbstract"]}/11**.',
      "- Independence reviewed pivotal Phase 3 primary results: **0**.",
      "",
      "| Exact FOCUS NCT | PubMed ID | Article title from PubMed | Source-only literal article scope flags | Exact NCT string found? |",
      "| --- | --- | --- | --- | --- |",
    ]
    for r in report["articleResearchLeads"]:
        title=r["articleTitleExactlyAsPubmed"].replace("|","/")[:160]
        flags=", ".join(r["literalSourceTextScopeFlags"]) or "None"
        lines.append(f'| {r["nct"]} | [{r["pmid"]}]({r["pubmedUrl"]}) | {title} | {flags} | {r["exactFocusNctIdentifierPresentInPubmedMetadataOrAbstract"]} |')
    lines.extend(["",
      "**Caution:** Even when an article contains the NCT, its results may be an earlier-phase component, a protocol, an exploratory analysis or background citations. A positive source abstract is not independently verified SAP-aligned efficacy.",
      "Zero official FDA predictions, method grades and independent reviewer signoffs; **ABSTAIN**.",
    ])
    return "\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--r69",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--summary",required=True,type=Path)
    p.add_argument("--raw-xml",required=True,type=Path)
    a=p.parse_args()
    files=[a.output,a.summary,a.raw_xml]
    require(len(set(files))==3 and all(not f.exists() and not f.is_symlink()
      and f.parent.is_dir() for f in files),
      "R70_ORIGINAL_SOURCE_RECEIPTS_MUST_BE_WRITE_ONCE")
    r69,mapping=read_original(a.r69)
    data,url=fetch_pubmed_xml(list(mapping))
    parsed=parse_pubmed_xml(data,mapping,source_url=url)
    report=build_report(R69_SHA,parsed,url)
    # No false success: write raw archive only once all 11 originals match.
    with a.raw_xml.open("xb") as f:f.write(data)
    with a.output.open("xb") as f:
        f.write((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
    with a.summary.open("xb") as f:f.write(summary(report).encode())
    print(json.dumps({k:report[k] for k in (
      "focusExactNcts","registryDerivedPubmedCitationLeads",
      "articleMetadataRecordsRetrieved",
      "exactNctIdentifiersFoundInRetrievedMetadataOrAbstract",
      "noExactNctIdentifierFoundInRetrievedMetadataOrAbstract",
      "articlesWithIndependentlyAdjudicatedPivotalOutcomes",
      "validatedFutureFdaApplicationPredictions"
    )},sort_keys=True))


if __name__=="__main__":
    main()
