#!/usr/bin/env python3
"""MAIN R57 Savara IMPALA-2 primary + secondary source readout against SAP.

All numerical values are transcribed and cross-checked from EXACT archived
current ClinicalTrials.gov JSON and the separately built R55 review packet.
Original source PDF SHA is matched to the R56 source-anchored SAP discrepancy
queue. The FDA outcome, SAP prospective lock and family-wise statistical tests
are NOT validated by the presence of low as-reported p-values.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from decimal import Decimal,InvalidOperation
import fitz
from scripts.reconcile_svra_original_protocol_sap_r56 import (
 NCT,APP,PROT,SAP,EXPECTED
)

SCHEMAS={
 "r53":"MAIN_R53_FOCUS_CURRENT_ORIGINAL_PROTOCOL_SAP_PDF_RESEARCH",
 "r55":"MAIN_R55_EXACT_23_APPLICATION_SOURCE_REPORTED_EFFICACY_SAFETY_METHOD_PACKETS",
 "r56":"MAIN_R56_SAVARA_SOURCE_PAGE_VERSUS_SAP_RECONCILIATION_QUEUE"
}

def _literal(value):
    return str(value) if isinstance(value,(int,float)) else value

def _decimal(value):
    if not isinstance(value,str) or not re.fullmatch(r"-?\d+(?:\.\d+)?",value):
        raise ValueError("MALFORMED_SOURCE_REPORTED_NUMERIC_LITERAL")
    try:return Decimal(value)
    except InvalidOperation:raise ValueError("MALFORMED_SOURCE_REPORTED_NUMERIC_LITERAL")

def _source_pdf(raw,filename,required_phrases):
    if not isinstance(raw,bytes) or hashlib.sha256(raw).hexdigest()!=EXPECTED[filename]["sha256"]:
        raise ValueError("SVRA_SOURCE_PDF_SHA_CHANGED")
    doc=fitz.open(stream=raw,filetype="pdf")
    if doc.needs_pass or doc.is_encrypted or len(doc)!=EXPECTED[filename]["pages"]:
        raise ValueError("SVRA_SOURCE_PDF_LAYOUT_CHANGED")
    cited=[]
    for page,phrase in required_phrases:
        actual=" ".join(doc[page-1].get_text("text",sort=True).split())
        ix=actual.casefold().find(phrase.casefold())
        if ix<0:raise ValueError("SVRA_REQUIRED_SAP_WORDING_MISSING_ON_SOURCE_PAGE")
        cited.append({
          "file":filename,"pdfPageOneBased":page,"literalSourcePhrase":phrase,
          "sourceExcerpt":" ".join(actual[max(0,ix-75):ix+len(phrase)+95].split())[:240]
        })
    return cited

def build(r53,r55,r56,raw_registry:bytes,raw_pdfs:dict[str,bytes]):
    if (not all(isinstance(x,dict) for x in (r53,r55,r56))
        or any(obj.get("schema")!=SCHEMAS[name] for name,obj in
            (("r53",r53),("r55",r55),("r56",r56)))
        or r53.get("nctRosterCount")!=29 or r53.get("applicationGroupCount")!=23
        or r53.get("originalPdfBodiesRetrieved")!=23
        or r53.get("validatedFDAForecasts")!=0
        or r55.get("nctTrials")!=29 or r55.get("applicationGroups")!=23
        or r55.get("sourceVerifiedCurrentProtocolSAPDocuments")!=23
        or len(r55.get("originalUniqueTrialEvidence",[]))!=29
        or len(r55.get("currentSourceCasePackets",[]))!=23
        or r55.get("independentlyValidatedFDAApplicationForecasts")!=0
        or r55.get("clinicalOrProductionWrites") is not False
        or r56.get("nct")!=NCT or r56.get("applicationCycleId")!=APP
        or r56.get("totalReviewItems")!=10
        or r56.get("explicitDiscrepancyReconciliationItems")!=6
        or r56.get("preReadoutOriginalSignedSapVersionsVerified")!=0
        or r56.get("independentlyValidatedApplicationFDAForecasts")!=0
        or r56.get("officialFDAOutcomePrediction")!="ABSTAIN"):
        raise ValueError("UNQUALIFIED_R53_R55_R56_EVIDENCE_CHAIN")
    trials=[x for x in r55["originalUniqueTrialEvidence"] if x.get("nct")==NCT]
    apps=[x for x in r55["currentSourceCasePackets"] if x.get("applicationCycleId")==APP]
    if (len(trials)!=1 or len(apps)!=1 or
        trials[0].get("applicationCycleIds")!=[APP] or apps[0].get("exactNcts")!=[NCT]):
        raise ValueError("INVALID_OR_MULTIPLIED_SAVARA_CYCLE_CROSSWALK")
    trial=trials[0]
    if (not isinstance(raw_registry,bytes) or
        hashlib.sha256(raw_registry).hexdigest()!=trial.get("currentRegistrySourceSha256")):
        raise ValueError("SVRA_CURRENT_REGISTRY_ORIGINAL_SHA_MISMATCH")
    study=json.loads(raw_registry)
    if study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")!=NCT:
        raise ValueError("ORIGINAL_SAVARA_NCT_DIFFERENT")
    outcomes=study.get("resultsSection",{}).get("outcomeMeasuresModule",{}).get("outcomeMeasures")
    ae=study.get("resultsSection",{}).get("adverseEventsModule",{})
    if not isinstance(outcomes,list) or not isinstance(ae,dict):
        raise ValueError("NO_ORIGINAL_POSTED_RESULTS_AVAILABLE")
    primary=[o for o in outcomes if o.get("type")=="PRIMARY"]
    if len(primary)!=1 or trial.get("reportedPrimaryStatisticalComparisons")!=1:
        raise ValueError("EXACT_SAVARA_PRIMARY_HYPOTHESIS_NOT_ONE")
    p=primary[0]
    group_id={g.get("id"):g.get("title") for g in p.get("groups",[])}
    if group_id!={"OG000":"Molgramostim","OG001":"Placebo"}:
        raise ValueError("SAVARA_PRIMARY_TREATMENT_COMPARISON_CHANGED")
    analyses=p.get("analyses") or []
    if len(analyses)!=1 or analyses[0].get("groupIds")!=["OG000","OG001"]:
        raise ValueError("UNVERIFIED_SAVARA_PRIMARY_COMPARISON")
    a=analyses[0]
    if a.get("ciPctValue")!="95" or a.get("ciNumSides")!="TWO_SIDED":
        raise ValueError("UNKNOWN_PRIMARY_CONFIDENCE_INTERVAL_METHOD")
    pval=a.get("pValue")
    if not isinstance(pval,str) or not Decimal("0")<=_decimal(pval)<=Decimal("1"):
        raise ValueError("PRIMARY_PVALUE_SOURCE_INVALID")
    est=a.get("paramValue");lo=a.get("ciLowerLimit");hi=a.get("ciUpperLimit")
    if not all(isinstance(x,str) for x in (est,lo,hi)):
        raise ValueError("SOURCE_ESTIMATE_OR_CI_MISSING")
    if not _decimal(lo)<=_decimal(est)<=_decimal(hi):
        raise ValueError("REPORTED_PRIMARY_EFFECT_ESTIMATE_OUTSIDE_95CI")
    reported=trial.get("postedPrimaryOutcomeTables")
    if (not isinstance(reported,list) or len(reported)!=1 or
        reported[0].get("titleAsPosted")!=p.get("title") or
        reported[0].get("timeFrameAsPosted")!=p.get("timeFrame")):
        raise ValueError("R55_PRIMARY_TITLE_TIMEFRAME_SOURCE_DIFFERENCE")
    x=reported[0].get("statisticalComparisons")
    if (not isinstance(x,list) or len(x)!=1 or
        x[0].get("reportedPValueLiteral")!=pval or
        x[0].get("reportedEstimateLiteral")!=est or
        x[0].get("reportedLowerBoundLiteral")!=lo or
        x[0].get("reportedUpperBoundLiteral")!=hi or
        x[0].get("nominalOrAdjustedStatusIndependentlyVerified") is not False):
        raise ValueError("R55_PRIMARY_STATISTICS_DIFFER_FROM_ARCHIVED_REGISTRY")
    arm_rows=ae.get("eventGroups")
    r55_arm=trial.get("postedAdverseEventArmCountsAsReported")
    if (not isinstance(arm_rows,list) or len(arm_rows)!=2 or
        not isinstance(r55_arm,list) or len(r55_arm)!=2):
        raise ValueError("EXPECTED_TWO_SAFETY_EXPOSURE_ARMS")
    safety=[]
    for g in arm_rows:
        other=next((q for q in r55_arm if q.get("groupId")==g.get("id")),None)
        if other is None:raise ValueError("R55_SAFETY_GROUP_ABSENT")
        if any(g.get(rawkey)!=other.get(key) for key,rawkey in (
            ("seriousAffected","seriousNumAffected"),("seriousAtRisk","seriousNumAtRisk"),
            ("otherAffected","otherNumAffected"),("otherAtRisk","otherNumAtRisk"),
            ("deathsAffected","deathsNumAffected"),("deathsAtRisk","deathsNumAtRisk"))):
            raise ValueError("R55_AE_DENOMINATOR_SOURCE_MISMATCH")
        name=g.get("title")
        if g.get("id") not in ("EG000","EG001") or name not in ("Molgramostim","Placebo"):
            raise ValueError("WRONG_SAVARA_SAFETY_GROUP")
        values={}
        for key in ("seriousNumAffected","seriousNumAtRisk","otherNumAffected",
                    "otherNumAtRisk","deathsNumAffected","deathsNumAtRisk"):
            n=g.get(key)
            if type(n) is not int or n<0:
                raise ValueError("INVALID_SOURCE_REPORTED_SAFETY_COUNT")
            values[key]=n
        for stem in ("serious","other","deaths"):
            if values[stem+"NumAffected"]>values[stem+"NumAtRisk"]:
                raise ValueError("SOURCE_AE_AFFECTED_EXCEEDS_RISK_SET")
        safety.append({"groupId":g["id"],"groupName":name,
             "sourceReportedAffectedAndDenominators":values,
             "clinicalRiskDifferenceOrCausalityAdjudicated":False})
    if len({g["groupId"] for g in safety})!=2:
        raise ValueError("DUPLICATE_SAFETY_ARMS")
    if set(raw_pdfs)!={PROT,SAP} or len(r56.get("verifiedCurrentPublicDocuments",[]))!=2:
        raise ValueError("R56_EXACT_ORIGINAL_PDF_PAIR_REQUIRED")
    pdfreceipts={d["file"]:d for d in r56["verifiedCurrentPublicDocuments"]}
    if set(pdfreceipts)!={PROT,SAP}:raise ValueError("R56_ORIGINAL_PDF_ID_DRIFT")
    for name in (PROT,SAP):
        if (hashlib.sha256(raw_pdfs[name]).hexdigest()!=pdfreceipts[name]["originalSha256"]
            or pdfreceipts[name].get("firstPublicPostingDateIndependentlyVerified") is not False):
            raise ValueError("R56_SOURCE_DOCUMENT_OR_FIRST_PUBLIC_CERTIFICATION_INVALID")
    methods=_source_pdf(raw_pdfs[SAP],SAP,[
        (25,"one primary efficacy endpoint and seven secondary"),
        (26,"DLCO at Week 24 is tested"),
        (26,"Hochberg method"),
        (27,"control-based imputation")
    ])
    protocol=_source_pdf(raw_pdfs[PROT],PROT,[
        (51,"average of the two best efforts"),
        (70,"alpha-splitting")
    ])
    reported_secondaries=[]
    for o in outcomes:
        if o.get("type")!="SECONDARY":continue
        groups=o.get("groups")
        if groups and {q.get("id") for q in groups}!={"OG000","OG001"}:
            raise ValueError("SAVARA_SECONDARY_GROUPS_CHANGED")
        for item in o.get("analyses") or []:
            val=item.get("pValue")
            if val is not None and (not isinstance(val,str) or not Decimal("0")<=_decimal(val)<=Decimal("1")):
                raise ValueError("SAVARA_SECONDARY_REPORTED_PVALUE_INVALID")
            reported_secondaries.append({
              "titleAsPosted":o.get("title"),"timeFrameAsPosted":o.get("timeFrame"),
              "reportedPValueLiteral":val,
              "reportedEffectEstimateLiteral":item.get("paramValue"),
              "reportedLower95CiLiteral":item.get("ciLowerLimit"),
              "reportedUpper95CiLiteral":item.get("ciUpperLimit"),
              "prespecifiedSAPFamilyMembershipIndependentlyValidated":False,
              "familyWiseAdjustedPValueOrClaim":None,
              "statisticalSignificanceIndependentlyAdjudicated":False
            })
    posted=study["protocolSection"].get("statusModule",{}).get("resultsFirstPostDateStruct",{}).get("date")
    if posted!=trial.get("resultsFirstPostedDateFromCurrentRecord"):
        raise ValueError("R55_FIRST_REGISTRY_RESULTS_DATE_SOURCE_MISMATCH")
    return {
      "schema":"MAIN_R57_SAVARA_SOURCE_PRIMARY_SAFETY_SAP_HIERARCHY_EVIDENCE",
      "generatedAtUtc":datetime.now(timezone.utc).isoformat(timespec="seconds"),
      "nct":NCT,"applicationCycleId":APP,
      "sourceRegistryOriginalSha256":hashlib.sha256(raw_registry).hexdigest(),
      "sourceRegistryCurrentResultsFirstPostedDate":posted,
      "protocolSourceSha256":pdfreceipts[PROT]["originalSha256"],
      "sapSourceSha256":pdfreceipts[SAP]["originalSha256"],
      "sourceReportedPrimaryEndpoint":{
        "title":p.get("title"),"timeFrame":p.get("timeFrame"),
        "armNamesFromRegistry":group_id,
        "reportedDifferenceVersusPlacebo":est,
        "reported95Ci":[lo,hi],"reportedPValue":pval,
        "sourceStatisticalMethod":a.get("statisticalMethod"),
        "sourceAnalysisComment":a.get("statisticalComment"),
        "independentNumericalRecalculation":False,
        "familyWiseAdjustedSignificanceValidated":False,
        "clinicalBenefitValidated":False
      },
      "sourceReportedSecondaryComparisons":reported_secondaries,
      "secondaryComparisonCount":len(reported_secondaries),
      "sourceReportedSafetyExposureArms":safety,
      "sapPlanPageCitations":methods,
      "protocolPlanPageCitations":protocol,
      "savaraDocumentReviewItemIds":[q["id"] for q in r56["pageAnchoredSourceReviewItems"]],
      "savaraSourceDiscrepancyReviewItems":r56["explicitDiscrepancyReconciliationItems"],
      "currentSapTitlePageDateAsReported":"2024-04-24",
      "currentProtocolTitlePageDateAsReported":"2024-10-09",
      "currentSAPIsNotCertifiedOriginalLockedVersion":True,
      "sourceReportedPValuesNotIndependentFwerValidation":True,
      "aeArmDenominatorsNotCausalTreatmentComparisons":True,
      "original29TrialAnd23ApplicationChainPreserved":True,
      "verifiedProspectiveSapAndAmendmentTimeline":False,
      "independentSignedEfficacyAssessment":False,
      "independentSignedBenefitRiskAssessment":False,
      "independentlyValidatedFdaPrediction":False,
      "scientificGrade":None,"approvalProbability":None,
      "realHistoricalBacktests":0,"measuredAccuracy":None,
      "modelTrainingAuthorized":False,"clinicalOrProductionWrites":False,
      "officialFdaOutcomeAndDelayPrediction":"ABSTAIN",
      "warning":"Current source-reported primary results and adverse-event numerators are not independently reanalysed, causal, or FDA-vetted. Low registry p-values are not proof of family-wise multiplicity validity, original prespecification, manufacturing adequacy, or final FDA action."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for label in ("r53","r55","r56","registry"):
        p.add_argument("--"+label,required=True,type=Path)
    p.add_argument("--pdf-dir",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists() or a.output.is_symlink() or not a.output.parent.is_dir():
        raise ValueError("IMMUTABLE_SAVARA_RESEARCH_OUTPUT_REQUIRED")
    data={}
    for label in ("r53","r55","r56"):
        path=getattr(a,label)
        if not path.is_file() or path.is_symlink() or path.stat().st_size>25_000_000:
            raise ValueError("UNSAFE_ORIGINAL_RESEARCH_RECEIPT")
        data[label]=json.loads(path.read_bytes())
    if (not a.registry.is_file() or a.registry.is_symlink() or
        a.registry.stat().st_size>10_000_000 or not a.pdf_dir.is_dir() or a.pdf_dir.is_symlink()):
        raise ValueError("UNSAFE_PUBLIC_REGISTRY_ORIGINAL")
    blobs={}
    for filename in (PROT,SAP):
        path=a.pdf_dir/filename
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(a.pdf_dir.resolve()):
            raise ValueError("NO_ORIGINAL_SOURCE_PDF")
        blobs[filename]=path.read_bytes()
    result=build(data["r53"],data["r55"],data["r56"],a.registry.read_bytes(),blobs)
    with a.output.open("xb") as f:f.write((json.dumps(result,indent=2,sort_keys=True)+"\n").encode())
    print(json.dumps({
       "nct":result["nct"],"reportedPrimaryPValue":result["sourceReportedPrimaryEndpoint"]["reportedPValue"],
       "reportedPrimaryDifference":result["sourceReportedPrimaryEndpoint"]["reportedDifferenceVersusPlacebo"],
       "secondaryComparisons":result["secondaryComparisonCount"],
       "independentlyValidatedFdaPrediction":result["independentlyValidatedFdaPrediction"],
       "officialFdaPrediction":result["officialFdaOutcomeAndDelayPrediction"]
    },sort_keys=True))

if __name__=="__main__":main()
