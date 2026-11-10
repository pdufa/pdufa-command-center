#!/usr/bin/env python3
"""MAIN R56 source-bound protocol/SAP reconciliation, not an FDA prediction.

Read the exact SHA-256 R54 PDF originals and R55 source-reported efficacy/safety
packet. Reconcile Savara protocol v10.0 and SAP v1.0 *method text*, record explicit
SAP Section 11 differences, and produce an amendment-history review queue for
all 23 application dossiers. This is a non-blinded current-source research
assessment; does not establish earlier public availability or SAP lock.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import date,datetime,timezone
from pathlib import Path
import fitz
from scripts.refresh_focus_public_sources_r40 import ROSTER,APPS,_read_json,build_manifest

NCT="NCT04544293"
APP="svra-molgramostim"
SHA=re.compile(r"[a-f0-9]{64}\Z")
METHODS={
 "PRIMARY_WEEK24_DLCO":(
     ("estimated treatment effect","week 24","p-value"),
     ("primary null hypothesis","week 24"),
     "SHARED_PRIMARY_ENDPOINT_DESCRIPTION_REQUIRES_ORIGINAL_VERSION_CHECK"),
 "FULL_ANALYSIS_SET":(
     ("full analysis set (fas)","all subjects randomized"),
     ("full analysis set (fas)","all randomized subjects"),
     "SHARED_RANDOMIZED_POPULATION_LANGUAGE_REQUIRES_EXPERT_VALIDATION"),
 "REPEATED_MEASURES_MODEL":(
     ("general linear mixed model","repeated measurements"),
     ("mixed model for repeated measurements","control-based imputation"),
     "BOTH_DOCUMENTS_DESCRIBE_REPEATED_MEASURES_REVIEW_COVARIATES"),
 "MULTIPLE_TESTING":(
     ("type i error control","sequential testing"),
     ("sequential testing","alpha splitting"),
     "BOTH_DESCRIBE_SEQUENTIAL_MULTIPLICITY_BUT_SAP_RECORDS_FIGURE_CORRECTION"),
 "MISSING_DATA":(
     ("control-based rule","missing"),
     ("control-based imputation","50 complete datasets"),
     "BOTH_DESCRIBE_CONTROL_BASED_IMPUTATION_SAP_ADDS_OPERATIONAL_DETAIL"),
 "SAFETY_ANALYSIS_SET":(
     ("safety analysis set","analyzed according"),
     ("safety analysis set (safs)","treatment received"),
     "BOTH_DESCRIBE_TREATMENT_RECEIVED_SAFETY_DENOMINATOR_REVIEW_REQUIRED"),
}
SAP_EXPLICIT_CHANGES={
 "DLCO_ACCEPTABLE_MEASUREMENT_AVERAGING":("average of the two best","all single acceptable"),
 "ALPHA_SPLITTING_FIGURE_CORRECTION":("alpha_1 alpha_2","do not fully match"),
 "SERIOUS_SAFETY_OBJECTIVE_TERMINOLOGY":(
    "frequency of serious adrs","frequency of serious treatment-related aes"),
}
MAX_PDF=55_000_000

def _page(doc,terms,*,minimum=1):
    for index in range(max(0,minimum-1),len(doc)):
        content=" ".join(doc[index].get_text("text",sort=True).casefold().split())
        if all(t in content for t in terms):
            return {"pdfPageOneBased":index+1,"matchedSourcePhrases":list(terms),
                    "sourceTextNotClinicalAdjudication":True}
    return None

def _verified_pdf(document,pdf_dir,nct):
    name=document.get("filename")
    if (not isinstance(name,str) or not re.fullmatch(r"(?:Prot|SAP|Prot_SAP)_[A-Za-z0-9_-]{1,36}\.pdf",name)
       or not isinstance(document.get("sourceSha256"),str) or
       not SHA.fullmatch(document["sourceSha256"])):
        raise ValueError("ORIGINAL_PDF_FILENAME_OR_HASH_INVALID")
    file=pdf_dir/(nct+"-"+name)
    if (not file.is_file() or file.is_symlink()
        or not file.resolve().is_relative_to(pdf_dir.resolve())
        or not 100<=file.stat().st_size<=MAX_PDF):
        raise ValueError("ORIGINAL_PDF_BYTES_MISSING_OR_UNSAFE")
    raw=file.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=document["sourceSha256"] or not raw.startswith(b"%PDF-"):
        raise ValueError("PDF_BYTES_DO_NOT_MATCH_R54_ORIGINAL")
    doc=fitz.open(stream=raw,filetype="pdf")
    if doc.needs_pass or doc.is_encrypted or len(doc)<1 or len(doc)>1800:
        raise ValueError("PDF_UNUSABLE_FOR_RECONCILIATION")
    return doc

def _date_or_none(x):
    if x is None:return None
    if not isinstance(x,str):raise ValueError("UNTRUSTED_DOCUMENT_DATE")
    try:return date.fromisoformat(x)
    except ValueError:raise ValueError("INVALID_DOCUMENT_DATE")

def reconcile(r54,r55,pdf_dir):
    m=build_manifest(_read_json(ROSTER),_read_json(APPS))
    if (m.get("trialCount")!=29 or m.get("applicationCount")!=23 or
        r54.get("schema")!="MAIN_R54_EIGHT_DOMAIN_PAGE_CITED_METHODS_EVIDENCE_MATRIX" or
        r54.get("canonicalTrials")!=29 or r54.get("applicationGroups")!=23 or
        r54.get("currentPdfDocumentsSourceVerified")!=23 or
        r54.get("historicalLockedSapVersionsIndependentlyVerified")!=0 or
        r54.get("independentlyValidatedApplicationFdaPredictions")!=0 or
        r54.get("modelTrainingAuthorized") is not False or
        r55.get("schema")!="MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS" or
        r55.get("nctTrials")!=29 or r55.get("applicationGroups")!=23 or
        r55.get("sourceVerifiedCurrentProtocolSAPDocuments")!=23 or
        r55.get("independentlyValidatedFDAApplicationForecasts")!=0 or
        r55.get("signedScientificReviews")!=0 or
        r55.get("modelTrainingAuthorized") is not False or
        not pdf_dir.is_dir() or pdf_dir.is_symlink()):
        raise ValueError("EXACT_29_23_ORIGINAL_R54_R55_INDEPENDENT_EVIDENCE_REQUIRED")
    member={x["nct"] for x in m["trialRows"]}
    trials=r54.get("trialMethodsReview");evidence=r55.get("originalUniqueTrialEvidence")
    apps=r54.get("applicationMethodsReview");cases=r55.get("currentSourceCasePackets")
    if (not isinstance(trials,list) or len(trials)!=29 or
        not isinstance(evidence,list) or len(evidence)!=29 or
        not isinstance(apps,list) or len(apps)!=23 or
        not isinstance(cases,list) or len(cases)!=23 or
        {x["nct"] for x in trials}!=member or
        {x["nct"] for x in evidence}!=member or
        len({x["nct"] for x in trials})!=29 or
        len({x["nct"] for x in evidence})!=29):
        raise ValueError("ORIGINAL_EXACT_NCT_ROSTER_OR_DUPLICATE_VIOLATION")
    groupids={x["cycleId"] for x in m["applicationGroups"]}
    if (len(groupids)!=23 or {x["applicationCycleId"] for x in cases}!=groupids or
        {x["applicationCycleId"] for x in apps}!=groupids):
        raise ValueError("ORIGINAL_EXACT_APPLICATION_ROSTER_VIOLATION")
    if (sum(len(x.get("documents",[])) for x in trials)!=23 or
        sum(bool(x.get("documents")) for x in trials)!=12 or
        sum(len(x.get("sourceMethodsPageReferences",[])) for x in evidence)!=23):
        raise ValueError("R54_R55_CURRENT_EXACT_23_DOCUMENT_CENSUS_MISMATCH")
    by_nct={x["nct"]:x for x in trials}
    original_by_nct={x["nct"]:x for x in evidence}
    group_by_nct={n:[] for n in member}
    for g in m["applicationGroups"]:
        for nct in g["ncts"]:
            if nct not in group_by_nct or g["cycleId"] in group_by_nct[nct]:
                raise ValueError("UNTRUSTED_ORIGINAL_TRIAL_APPLICATION_GROUP")
            group_by_nct[nct].append(g["cycleId"])
    summary=[]
    for n in sorted(member):
        record=by_nct[n]
        if (record["applicationCycleIds"]!=sorted(group_by_nct[n]) or
            record["sourceDocumentCount"]!=len(record["documents"]) or
            len(record["documents"])>2 or
            record.get("independentStatisticalReviewComplete") is not False):
            raise ValueError("UNREVIEWED_OR_MISMATCHED_TRIAL_METHOD_SOURCE")
        ds=record["documents"]
        for d in ds:
            if not isinstance(d.get("sourceSha256"),str) or not SHA.fullmatch(d["sourceSha256"]):
                raise ValueError("SOURCE_PDF_HASH_REQUIRED")
        references=original_by_nct[n]["sourceMethodsPageReferences"]
        if ({(d["filename"],d["sourceSha256"]) for d in ds}!=
            {(d["filename"],d["sha256"]) for d in references}):
            raise ValueError("R54_R55_ORIGINAL_PDF_DIGEST_DISAGREEMENT")
        protocols=[d for d in ds if d["protocolFlagFromCurrentRegistry"]]
        saps=[d for d in ds if d["sapFlagFromCurrentRegistry"]]
        protocol_dates=[_date_or_none(d["currentRegistryDocumentDateAsReported"]) for d in protocols]
        sap_dates=[_date_or_none(d["currentRegistryDocumentDateAsReported"]) for d in saps]
        earlier=bool(protocol_dates and sap_dates and
                   all(x is not None for x in protocol_dates+sap_dates) and
                   min(sap_dates)<max(protocol_dates))
        summary.append({
            "nct":n,"applicationCycleIds":sorted(group_by_nct[n]),
            "currentDocumentCount":len(ds),
            "currentProtocolPdfAvailable":bool(protocols),
            "currentSapPdfAvailable":bool(saps),
            "sapDocumentDatePrecedesAtLeastOneCurrentProtocolDate":earlier,
            "documentDatesAndAvailableVersionsAreNotOriginalReleaseClock":True,
            "historicalAmendmentChainIndependentlyReconciled":False,
            "statisticalGrade":None,"officialFDAForecast":"ABSTAIN"
        })
    svra=by_nct[NCT];source=original_by_nct[NCT]
    if (svra["applicationCycleIds"]!=[APP] or
        source["applicationCycleIds"]!=[APP] or
        len(svra["documents"])!=2):
        raise ValueError("SVRA_EXACT_ONE_APPLICATION_TWO_SOURCE_DOCUMENTS_REQUIRED")
    protocol, sap=None,None
    for record in svra["documents"]:
        if record["filename"]=="Prot_000.pdf":protocol=record
        if record["filename"]=="SAP_001.pdf":sap=record
    if protocol is None or sap is None:
        raise ValueError("SVRA_ORIGINAL_PROTOCOL_AND_SAP_NOT_IDENTIFIED")
    if (protocol["currentRegistryDocumentDateAsReported"]!="2024-10-09" or
        sap["currentRegistryDocumentDateAsReported"]!="2024-04-24"):
        raise ValueError("SVRA_REPORTED_DOCUMENT_DATE_CHANGED_NEEDS_NEW_REVIEW")
    p=_verified_pdf(protocol,pdf_dir,NCT)
    s=_verified_pdf(sap,pdf_dir,NCT)
    if len(p)!=134 or len(s)!=89:
        raise ValueError("SVRA_DOCUMENT_PAGES_DRIFTED")
    matched=[]
    for key,(pa,sa,meaning) in METHODS.items():
        p_hit=_page(p,pa,minimum=15)
        s_hit=_page(s,sa,minimum=15)
        if p_hit is None or s_hit is None:
            raise ValueError("SVRA_PAIRED_SOURCE_METHOD_ANCHOR_MISSING_"+key)
        matched.append({
          "method":key,"protocolSource":{"url":protocol["sourceUrl"],
                       "sha256":protocol["sourceSha256"],**p_hit},
          "sapSource":{"url":sap["sourceUrl"],"sha256":sap["sourceSha256"],**s_hit},
          "comparison":"METHOD_DESCRIPTIONS_BROADLY_CONCORDANT_WITH_UNRESOLVED_VERSION_AND_EXECUTION_DETAILS",
          "reviewPoint":meaning,
          "prespecificationAndModelAdequacyIndependentlyValidated":False
        })
    changes=[]
    for key,terms in SAP_EXPLICIT_CHANGES.items():
        lead=_page(s,terms,minimum=15)
        if lead is None:raise ValueError("SVRA_SAP_SECTION_11_EXPLICIT_CHANGE_NOT_FOUND_"+key)
        changes.append({
          "issue":key,"sapSource":{"url":sap["sourceUrl"],"sha256":sap["sourceSha256"],**lead},
          "sourceDescribesProtocolDifference":True,
          "changeOccurredBeforeOriginalUnblindingIndependentlyVerified":False,
          "clinicalOrRegulatoryMaterialityIndependentlyAdjudicated":False,
          "nextAction":"RECONCILE_WITH_ORIGINAL_PROTOCOL_REVISION_AND_SIGNED_SAP_RELEASE_TIMELINE"
        })
    stats=source.get("postedPrimaryOutcomeTables") or []
    if not stats or not stats[0].get("statisticalComparisons"):
        raise ValueError("ORIGINAL_SVRA_POSTED_PRIMARY_STATISTICAL_COMPARISON_MISSING")
    primary=stats[0]["statisticalComparisons"][0]
    expected={"reportedPValueLiteral":"0.0007","reportedEstimateLiteral":"6.0",
             "reportedLowerBoundLiteral":"2.5","reportedUpperBoundLiteral":"9.4"}
    if any(str(primary.get(k))!=v for k,v in expected.items()):
        raise ValueError("SVRA_CURRENT_REGISTRY_PRIMARY_NUMBERS_SOURCE_DRIFT")
    aes=source.get("postedAdverseEventArmCountsAsReported") or []
    if [(x.get("seriousAffected"),x.get("seriousAtRisk")) for x in aes]!=[(14,81),(20,83)]:
        raise ValueError("SVRA_CURRENT_REGISTRY_SAFETY_ARMS_SOURCE_DRIFT")
    if source.get("currentRegistrySourceSha256")!=svra.get("currentRegistrySourceSha256"):
        raise ValueError("SVRA_REGISTRY_PRIMARY_AND_METHOD_DIFFERENT_SOURCE_VERSIONS")
    conditional_p_value=float(primary["reportedPValueLiteral"])
    if not (0<=conditional_p_value<=1):raise ValueError("INVALID_REPORTED_P_VALUE")
    return {
      "schema":"MAIN_R56_SAVARA_PROTOCOL_SAP_CLINICAL_METHOD_EXCEPTION_REVIEW",
      "observedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "canonicalTrials":29,"applicationGroups":23,
      "trialDocumentChronologyResearch":summary,
      "trialCasesWithCurrentProtocolAndSap":sum(x["currentProtocolPdfAvailable"] and x["currentSapPdfAvailable"] for x in summary),
      "trialsWithSapDocumentDatedBeforeAttachedProtocol":sum(x["sapDocumentDatePrecedesAtLeastOneCurrentProtocolDate"] for x in summary),
      "savara":{
        "nct":NCT,"applicationCycleId":APP,
        "drug":"molgramostim","trial":"IMPALA-2",
        "currentProtocolVersionAsPrinted":"10.0",
        "currentProtocolDateAsRegistry":"2024-10-09",
        "sapVersionAsPrinted":"1.0",
        "sapDateAsRegistry":"2024-04-24",
        "laterProtocolDateThanSap":True,
        "pairedMethodDescriptionFindings":matched,
        "explicitSapReportedProtocolDifferences":changes,
        "currentRegistryPrimaryOutcome":{
          "pValueAsPublished":primary["reportedPValueLiteral"],
          "estimatedDifferenceAsPublished":primary["reportedEstimateLiteral"],
          "confidenceIntervalLowerAsPublished":primary["reportedLowerBoundLiteral"],
          "confidenceIntervalUpperAsPublished":primary["reportedUpperBoundLiteral"],
          "publishedNumericalPBelowNominalTwoSidedAlphaPointZeroFive":
              conditional_p_value<0.05,
          "thisIsAConditionalNominalReadingNotAnIndependentlyRecalculatedPValue":True,
          "originalProspectiveMultiplicityAndEndpointAdequacyValidated":False,
          "FDAOutcomeInferenceAllowed":False
        },
        "currentRegistryReportedSafetyArms":[
          {"groupId":x.get("groupId"),"groupName":x.get("groupName"),
           "seriousAffectedAsReported":x.get("seriousAffected"),
           "seriousAtRiskAsReported":x.get("seriousAtRisk"),
           "causalEffectOrPooledRiskInferred":False} for x in aes
        ],
        "originalPublicReleaseOfSapBeforeReadoutIndependentlyVerified":False,
        "signedLockedSapAndFullProtocolAmendmentChainVerified":False,
        "independentStatisticalAnalystSigned":False,
        "independentBenefitRiskReviewSigned":False,
        "scientificGrade":None,"numericalFDAProbability":None,
        "officialOutcomeAndDelayPrediction":"ABSTAIN",
        "nextScientificReviewQuestions":[
          "Verify first public release and all signed SAP/protocol revisions before unblinding",
          "Reconcile DLCO averaging methods (two best efforts versus all acceptable)",
          "Reconcile alpha schema correction and regional endpoint families with original version history",
          "Independently re-run protocol-specified MMRM and imputations using permitted trial data if available",
          "Verify Week 24 outcome units, estimand and clinical meaningfulness separately from nominal p",
          "Review arm-level exposure, serious adverse-event coding, deaths and available regulator/CMC issues"
        ]
      },
      "sourceDocumentTextComparisonNotStatisticalReviewerCertification":True,
      "independentScientificSignoffs":0,
      "validatedFDAForecasts":0,
      "realHistoricalPredictionBacktests":0,
      "measuredFDAAccuracy":None,
      "modelTrainingAuthorized":False,
      "productionOrClinicalLedgerWrites":False,
      "warning":"High-level concordance and source-acknowledged deviations from current posted PDFs do not establish protocol lock, posthoc changes, medical significance, or FDA approval. Nominal reported p is not independently recalculated or regulatory-grade."
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r54-matrix",type=Path,required=True)
    parser.add_argument("--r55-packets",type=Path,required=True)
    parser.add_argument("--pdf-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.output.is_symlink() or not args.output.parent.is_dir():
        raise ValueError("IMMUTABLE_RESEARCH_OUTPUT_REQUIRED")
    for path in (args.r54_matrix,args.r55_packets):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>20_000_000:
            raise ValueError("SOURCE_RESEARCH_PACKET_UNAVAILABLE_OR_UNSAFE")
    result=reconcile(json.loads(args.r54_matrix.read_bytes()),
                     json.loads(args.r55_packets.read_bytes()),args.pdf_dir)
    with args.output.open("xb") as f:f.write(
        (json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
      "canonicalTrials","applicationGroups","trialCasesWithCurrentProtocolAndSap",
      "trialsWithSapDocumentDatedBeforeAttachedProtocol",
      "independentScientificSignoffs","validatedFDAForecasts"
    )},sort_keys=True),flush=True)

if __name__=="__main__":main()
