#!/usr/bin/env python3
"""MAIN R54: provenance-gated FOCUS 23 application protocol/SAP review packets.

Joins two immutable, independently executed source archives (R51 and R53).
Current-study ClinicalTrials.gov bytes must agree before reported efficacy or
safety data are paired with PDF-review leads. No original SAP public clock,
prospective multiplicity proof, medical conclusion or FDA forecast is inferred.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from scripts.refresh_focus_public_sources_r40 import ROSTER, APPS, _read_json, build_manifest

HEX = re.compile(r"[a-f0-9]{64}\Z")
PDF = re.compile(r"NCT[0-9]{8}-(?:Prot|SAP|Prot_SAP)_[A-Za-z0-9_-]{1,36}\.pdf\Z")
KEYWORDS = frozenset({
    "primary endpoint", "primary outcome", "statistical analysis plan",
    "multiplicity", "hierarchical testing", "type i error", "missing data",
    "interim analysis", "intention-to-treat", "intention to treat",
    "protocol amendment", "version history", "treatment-emergent",
    "adverse event", "safety population", "alpha"
})
PRIORITY = ("svra-molgramostim", "capr-deramiocel", "cogt-gist")

def _index(rows, field, n, label):
    if not isinstance(rows, list) or len(rows) != n:
        raise ValueError(label + "_COUNT_MISMATCH")
    if any(not isinstance(x, dict) or not isinstance(x.get(field), str)
           or not x[field] for x in rows):
        raise ValueError(label + "_IDENTITY_MALFORMED")
    d = {x[field]: x for x in rows}
    if len(d) != n:
        raise ValueError(label + "_DUPLICATE")
    return d

def _verify_pdf(row, root):
    filename = row.get("archivedPdfFilename")
    nct = row.get("nct")
    if (not isinstance(nct,str) or not isinstance(filename,str)
        or not PDF.fullmatch(filename)
        or not filename.startswith(nct + "-")):
        raise ValueError("PDF_IDENTITY_OR_PATH_UNSAFE")
    digest = row.get("sourceSha256")
    if not isinstance(digest,str) or not HEX.fullmatch(digest):
        raise ValueError("PDF_ORIGINAL_SHA_MISSING")
    path = root / filename
    if (not path.is_file() or path.is_symlink() or
        not path.resolve().is_relative_to(root.resolve())
        or path.stat().st_size > 55_000_000):
        raise ValueError("PDF_ARCHIVED_ORIGINAL_MISSING")
    original = path.read_bytes()
    if (not original.startswith(b"%PDF-") or
        len(original) != row.get("sourceBytes") or
        hashlib.sha256(original).hexdigest() != digest):
        raise ValueError("PDF_ORIGINAL_BYTES_SHA_MISMATCH")
    evidence = row.get("pdfResearch")
    if (not isinstance(evidence,dict) or
        evidence.get("statisticalPrespecificationValidated") is not False or
        evidence.get("regulatoryConclusionAuthorized") is not False or
        evidence.get("sourceDocumentTextHumanReviewed") is not False or
        not isinstance(evidence.get("pageCount"),int) or evidence["pageCount"]<1):
        raise ValueError("PDF_SCIENTIFIC_CERTIFICATION_OR_PAGE_INVALID")
    leads = evidence.get("keywordSourceExcerpts")
    if not isinstance(leads,list) or len(leads)>28:
        raise ValueError("PDF_SOURCE_EXCERPTS_UNVERIFIED")
    safe_leads=[]
    for lead in leads:
        if (not isinstance(lead,dict) or lead.get("term") not in KEYWORDS
            or type(lead.get("pdfPageOneBased")) is not int or
            not 1 <= lead["pdfPageOneBased"] <= evidence["pageCount"]
            or not isinstance(lead.get("sourceTextExcerpt"),str)
            or not 0 < len(lead["sourceTextExcerpt"]) <= 260):
            raise ValueError("PDF_PAGE_EVIDENCE_LEAD_MALFORMED")
        safe_leads.append(dict(lead))
    return {
        "nct":nct, "filename":row["filename"],
        "pdfSourceUrl":row["sourceUrl"], "pdfOriginalSha256":digest,
        "pdfBytes":len(original), "pdfPages":evidence["pageCount"],
        "documentDateFromCurrentRegistryMetadata":row.get("currentRegistryDocumentDate"),
        "hasProtocolFlag":row.get("hasProtocolFlag") is True,
        "hasSapFlag":row.get("hasSapFlag") is True,
        "searchLeads":safe_leads,
        "firstPublicAvailabilityOfThisVersionVerified":False,
        "originalPreReadoutLockAndMultiplicityVerified":False,
    }

def build(manifest, efficacy, document, pdf_root):
    if (manifest.get("trialCount") != 29 or manifest.get("applicationCount") != 23 or
        len(manifest.get("trialRows",[])) != 29 or
        len(manifest.get("applicationGroups",[])) != 23):
        raise ValueError("EXACT_ORIGINAL_29_23_ROSTER_REQUIRED")
    if (not isinstance(efficacy,dict) or
        efficacy.get("schema") != "MAIN_R51_FOCUS_23_SOURCE_REPORTED_EFFICACY_AND_SAFETY_DOSSIERS" or
        efficacy.get("trialRosterCount") != 29 or efficacy.get("applicationDossierCount") != 23 or
        efficacy.get("validatedFDAForecasts") != 0 or
        efficacy.get("productionOrClinicalLedgerWrites") is not False or
        not isinstance(document,dict) or
        document.get("schema") != "MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH" or
        document.get("nctRosterCount") != 29 or document.get("applicationGroupCount") != 23 or
        document.get("currentRegistryDocumentEntries") != 23 or
        document.get("originalPdfBodiesRetrieved") != 23 or
        document.get("validatedFDAForecasts") != 0 or
        document.get("clinicalOrProductionWrites") is not False):
        raise ValueError("EXACT_SOURCE_RESEARCH_REPORTS_NOT_QUALIFIED")
    if not pdf_root.is_dir() or pdf_root.is_symlink():
        raise ValueError("ORIGINAL_PUBLIC_PDF_ARCHIVE_REQUIRED")
    e_app = _index(efficacy.get("applicationDossiers"), "applicationCycleId", 23, "R51_APPLICATION")
    d_app = _index(document.get("applicationResearch"), "applicationCycleId", 23, "R53_APPLICATION")
    e_trials = _index(efficacy.get("trialEvidence"), "nct", 29, "R51_NCT")
    roster={x["nct"] for x in manifest["trialRows"]}
    if set(e_trials)!=roster:
        raise ValueError("ORIGINAL_TRIAL_ROSTER_DISAGREES_WITH_EFFICACY")
    pdfs = document.get("documentResearch")
    if not isinstance(pdfs,list) or len(pdfs)!=23:
        raise ValueError("ORIGINAL_DOCUMENT_RECORD_COUNT_MISMATCH")
    grouped={}
    seen=set()
    for src in pdfs:
        key=(src.get("nct"),src.get("filename"))
        if key in seen or key[0] not in roster:
            raise ValueError("DUPLICATED_OR_NONORIGINAL_PDF_ID")
        seen.add(key)
        item = _verify_pdf(src, pdf_root)
        grouped.setdefault(key[0],[]).append(item)
    all_docs = sum(len(v) for v in grouped.values())
    if all_docs != 23:
        raise ValueError("SOURCE_DOCUMENT_COUNT_CHANGED")
    studies=[]
    for original in manifest["applicationGroups"]:
        cid=original["cycleId"]
        current=e_app.get(cid);research=d_app.get(cid)
        if not current or not research or current.get("exactNctIds")!=original["ncts"] or research.get("exactNcts")!=original["ncts"]:
            raise ValueError("APPLICATION_TRIAL_CROSSWALK_CHANGED")
        rows=[]
        for n in original["ncts"]:
            t=e_trials[n]
            pdf_rows=sorted(grouped.get(n,[]),key=lambda x:x["filename"])
            declared={(x.get("filenameAsRegistry"),x.get("documentDateAsRegistry")):
                      (x.get("hasProtocolFlagAsRegistry"),x.get("hasSapFlagAsRegistry"))
                      for x in t.get("currentProtocolSapAttachments",[])}
            expected={(x["filename"].split(n+"-",1)[-1],x["documentDateFromCurrentRegistryMetadata"]):
                      (x["hasProtocolFlag"],x["hasSapFlag"]) for x in pdf_rows}
            if len(declared)!=len(t.get("currentProtocolSapAttachments",[])) or declared!=expected:
                raise ValueError("R51_R53_PDF_METADATA_AND_ATTACHMENT_CROSSWALK_MISMATCH")
            recorded=t.get("currentRegistrySourceSha256")
            if recorded is not None and (not isinstance(recorded,str) or not HEX.fullmatch(recorded)):
                raise ValueError("R51_REGISTRY_SHA_MALFORMED")
            # A source-version comparison across two independent runs needs the R46
            # original-registry SHA in a separate input; until then mark unverified.
            current_source_versions_proven_same=False
            if t.get("postedPrimaryOutcomeCount",0)<0 or t.get("postedSafetyEventGroups",0)<0:
                raise ValueError("R51_POSTED_MODULE_COUNT_INVALID")
            rows.append({
                "nct":n,
                "sourceReportedPrimaryTables":t.get("postedPrimaryOutcomeCount",0),
                "sourceReportedPrimaryStatisticalAnalysisEntries":sum(
                     len(x.get("statisticalAnalyses",[])) for x in t.get("primary",[])),
                "sourceReportedSeriousEventTermEntries":len(t.get("seriousEventTerms",[])),
                "sourceReportedOtherEventTermEntries":len(t.get("otherEventTerms",[])),
                "postedResultVsCurrentRegisteredTitleTimeframeChecks":
                    t.get("primaryTitleTimeframeConcordance",[]),
                "sourceReportedResultsFirstPostedDate":t.get("currentRegistryResultsFirstPostDateAsReported"),
                "currentRegistryCapturedSourceSha256":recorded,
                "pdfProtocolSapSourceLeads":pdf_rows,
                "crossRunRegistrySnapshotBytesIndependentlyMatched":current_source_versions_proven_same,
                "preUnblindingPrespecifiedEndpointHierarchyVerified":False,
                "clinicalEfficacyOrSafetyConclusionAdjudicated":False,
            })
        has_p=any(x["sourceReportedPrimaryTables"]>0 for x in rows)
        has_s=any(x["sourceReportedSeriousEventTermEntries"] or x["sourceReportedOtherEventTermEntries"] for x in rows)
        has_pdf=any(x["pdfProtocolSapSourceLeads"] for x in rows)
        has_sap=any(any(y["hasSapFlag"] for y in x["pdfProtocolSapSourceLeads"]) for x in rows)
        questions=[
          "Determine original public availability of protocol/SAP versions relative to first unblinding and results",
          "Reconcile endpoints and multiplicity against prospectively locked SAP, not current registry metadata",
          "Independent benefit-risk, adverse-event denominator and FDA manufacturing review needed"
        ]
        if not has_p:questions.append("Find source-reported primary results outside current registry")
        if not has_s:questions.append("Find arm-specific exposure and safety outside current registry")
        if not has_sap:questions.append("Locate original statistical analysis plan outside current registry")
        studies.append({
            "applicationCycleId":cid,
            "ticker":original.get("ticker"),
            "exactNctIds":list(original["ncts"]),
            "priorityEarliestReportedReview":cid in PRIORITY,
            "currentRegistryPrimaryOutcomeTables":sum(x["sourceReportedPrimaryTables"] for x in rows),
            "currentRegistryStatisticalAnalysisRows":sum(x["sourceReportedPrimaryStatisticalAnalysisEntries"] for x in rows),
            "currentRegistrySeriousEventTermRows":sum(x["sourceReportedSeriousEventTermEntries"] for x in rows),
            "currentRegistryOtherEventTermRows":sum(x["sourceReportedOtherEventTermEntries"] for x in rows),
            "sourceArchiveHasProtocolOrSapPdf":has_pdf,
            "sourceArchiveHasSapPdf":has_sap,
            "clinicalEvidenceTaskList":questions,
            "trialReviewPackets":rows,
            "preReadoutOriginalSAPVersionVerified":False,
            "clinicalStatisticalReviewerSigned":False,
            "independentBenefitRiskConclusion":None,
            "validatedFDAOutcomeForecast":None,
            "fdaForecastStatus":"ABSTAIN",
            "quantitativeFdaProbability":None,
        })
    return {
        "schema":"MAIN_R54_23_FOCUS_APPLICATION_EFFICACY_SAFETY_AND_PDF_SOURCE_REVIEW",
        "observedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "trialCount":29,"applicationCount":23,
        "protocolSapOriginalPdfFilesShaVerified":23,
        "applicationsWithOriginalCurrentDocumentPdf":sum(x["sourceArchiveHasProtocolOrSapPdf"] for x in studies),
        "applicationsWithCurrentSapPdf":sum(x["sourceArchiveHasSapPdf"] for x in studies),
        "applicationsWithSourceReportedPrimaryResults":sum(x["currentRegistryPrimaryOutcomeTables"]>0 for x in studies),
        "applicationsWithReportedSeriousEventTerms":sum(x["currentRegistrySeriousEventTermRows"]>0 for x in studies),
        "applications":studies,
        "crossRunCurrentRegistryVersionsFullyVerifiedEqual":False,
        "historicalFirstPublicationClockVerified":False,
        "prespecifiedSAPBeforeUnblindingVerified":False,
        "independentlySignedStatisticalEfficacyAssessments":0,
        "independentlySignedBenefitRiskAssessments":0,
        "validatedFDAOutcomePredictions":0,
        "historicalIndependentBacktests":0,
        "measuredCalibration":None,"approvalProbability":None,
        "trainOrAutopredictAuthorized":False,"productionMutationAuthorized":False,
        "status":"SOURCE_LINKED_HUMAN_RESEARCH_QUEUE_NOT_ADJUDICATED",
        "note":"Verified 23 downloaded PDF hashes and per-NCT document metadata, but R51 current registry and R53 captured current document metadata are independent-run snapshots. A common original registry byte fingerprint is not available in this join; all statistical review leads remain research-only. A PDF's document date is not first-publication date."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--efficacy",required=True,type=Path)
    p.add_argument("--pdf-report",required=True,type=Path)
    p.add_argument("--pdf-original-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    for path in [a.efficacy,a.pdf_report]:
        if not path.is_file() or path.is_symlink() or path.stat().st_size>15_000_000:
            raise ValueError("IMMUTABLE_SOURCE_REPORT_NOT_AVAILABLE")
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("WRITE_ONCE_REVIEW_OUTPUT_REQUIRED")
    manifest=build_manifest(_read_json(ROSTER),_read_json(APPS))
    result=build(manifest,json.loads(a.efficacy.read_bytes()),
                 json.loads(a.pdf_report.read_bytes()),a.pdf_original_dir)
    with a.output.open("xb") as f:
        f.write((json.dumps(result,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({k:result[k] for k in (
        "trialCount","applicationCount","protocolSapOriginalPdfFilesShaVerified",
        "applicationsWithOriginalCurrentDocumentPdf","applicationsWithCurrentSapPdf",
        "applicationsWithSourceReportedPrimaryResults","validatedFDAOutcomePredictions",
        "status")},sort_keys=True),flush=True)

if __name__=="__main__":main()
