#!/usr/bin/env python3
"""MAPLE-HCM published continuous exercise endpoint review packet, NOT adjudication.

Original NEJM abstract and secondary ACC trial summary have separate roles.
This script deliberately does not infer a binary response, pooled odds ratio,
clinical benefit-risk approval or source authentication from either.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/scientific-levels1-6/maple-hcm-source-review-20261114.json"
NEJM = "https://www.nejm.org/doi/10.1056/NEJMoa2504654"
ACC = "https://www.acc.org/latest-in-cardiology/clinical-trials/2025/09/23/17/49/maple-hcm"
TOP = {"schemaVersion","kind","nct","trialName","drug","comparator","indication",
       "evidenceCutoffDate","sources","registryPhaseUnreviewed","studyDesign",
       "primaryEndpoint","secondaryEndpoints","safety","evidenceLimitationsUnreviewed",
       "reviewQuestions","sourceIndependentlyAuthenticated",
       "originalClinicalTablesAuthenticated","qualifiedClinicalReviewCompleted",
       "independentStatisticalReviewCompleted","finalAdjudicationCompleted",
       "verifiedFdaApplicationCycle","clinicalScore","approvalProbability",
       "fdaOutcomeJudgment","blindHistoricalPredictionPermitted"}
SOURCE_FIELDS = {"role","url","publishedDate","locator","originalSourceIndependentlyAuthenticated"}
EXPECTED_SECONDARY = {
    "NYHA_CLASS_IMPROVEMENT_W24": ("COMPARATIVE_PERCENTAGE_POINT",25,"percentage points",(11,39),"<0.001"),
    "KCCQ_CSS_W24": ("COMPARATIVE_MEAN_CHANGE",6.9,"points",(2.6,11.3),"0.002"),
    "VALSALVA_LVOT_GRADIENT_W24": ("COMPARATIVE_MEAN_CHANGE",-34.9,"mm Hg",(-43.4,-26.4),"<0.001"),
    "NT_PROBNP_PROPORTIONAL_CHANGE_W24": ("RATIO",0.19,"ratio",(0.15,0.24),"<0.001"),
    "LEFT_ATRIAL_VOLUME_INDEX_W24": ("COMPARATIVE_MEAN_CHANGE",-7.0,"mL/m²",(-9.1,-4.9),"<0.001"),
    "LEFT_VENTRICULAR_MASS_INDEX_W24": ("COMPARATIVE_MEAN_CHANGE",-4.9,"g/m²",(-11.7,2.0),"0.16"),
}
SECONDARY_FIELDS={"id","type","name","effect","unit","ci95","pValue","reportedBy"}


def keys(row, required, description):
    if not isinstance(row,dict) or set(row) != set(required):
        raise ValueError("Missing or forbidden fields: "+description)


def source_validate(sources):
    if not isinstance(sources,list) or len(sources)!=2:
        raise ValueError("Both original NEJM and secondary ACC evidence needed")
    indexed={}
    for s in sources:
        if not isinstance(s,dict):
            raise ValueError("Invalid publisher source")
        role=s.get("role")
        if role in indexed:
            raise ValueError("Duplicate source role")
        if role=="ORIGINAL_PEER_REVIEWED_ABSTRACT":
            keys(s,SOURCE_FIELDS | {"pmid","doi"},"NEJM source")
            if (s["url"]!=NEJM or s["pmid"]!="40888697"
                or s["doi"]!="10.1056/NEJMoa2504654"
                or s["publishedDate"]!="2025-08-30"):
                raise ValueError("NEJM source misattributed")
        elif role=="INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT":
            keys(s,SOURCE_FIELDS | {"updatedDate"},"ACC source")
            if (s["url"]!=ACC or s["publishedDate"]!="2025-09-24"
                    or s["updatedDate"]!="2025-11-09"):
                raise ValueError("Secondary ACC article identity misattributed")
        else:
            raise ValueError("Unsupported original or secondary source")
        if (s["originalSourceIndependentlyAuthenticated"] is not False
                or not isinstance(s["locator"],str) or not s["locator"].strip()):
            raise ValueError("Research metadata cannot authenticate sources")
        indexed[role]=s
    if set(indexed)!={"ORIGINAL_PEER_REVIEWED_ABSTRACT",
                     "INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT"}:
        raise ValueError("Original journal and ACC sources must be distinct")
    return indexed


def assess(record):
    keys(record,TOP,"MAPLE-HCM research-only record")
    if (type(record["schemaVersion"]) is not int or record["schemaVersion"]!=1
            or record["kind"]!="MAPLE_HCM_PUBLICATION_ABSTRACT_AND_ACC_SUMMARY_UNREVIEWED"
            or record["nct"]!="NCT05767346" or record["trialName"]!="MAPLE-HCM"
            or record["drug"]!="aficamten"
            or record["comparator"]!="metoprolol succinate"
            or record["indication"]!="symptomatic obstructive hypertrophic cardiomyopathy"
            or record["evidenceCutoffDate"]!="2026-11-14"
            or record["registryPhaseUnreviewed"]!=["PHASE3"]):
        raise ValueError("Exact trial, disease, phase or current cutoff mismatch")
    for key in ("sourceIndependentlyAuthenticated",
                "originalClinicalTablesAuthenticated","qualifiedClinicalReviewCompleted",
                "independentStatisticalReviewCompleted","finalAdjudicationCompleted",
                "verifiedFdaApplicationCycle","blindHistoricalPredictionPermitted"):
        if record[key] is not False:
            raise ValueError("Clinical research cannot certify " + key)
    for key in ("clinicalScore","approvalProbability","fdaOutcomeJudgment"):
        if record[key] is not None:
            raise ValueError("Clinical study publication cannot assign score/FDA outcome")
    source_validate(record["sources"])
    trial=record["studyDesign"]
    keys(trial,{"design","randomized","treatmentWeeks","allocation","doseArms",
                "baselineMeanAgeYears","baselineMalePercent","comparatorIsActiveDrug",
                "placeboOnlyControl","population"},"MAPLE-HCM trial")
    if (trial["design"]!="INTERNATIONAL_DOUBLE_BLIND_DOUBLE_DUMMY_ACTIVE_COMPARATOR"
            or type(trial["randomized"]) is not int or trial["randomized"]!=175
            or type(trial["treatmentWeeks"]) is not int or trial["treatmentWeeks"]!=24
            or trial["allocation"]!="1:1" or trial["comparatorIsActiveDrug"] is not True
            or trial["placeboOnlyControl"] is not False
            or trial["baselineMeanAgeYears"]!=58
            or trial["baselineMalePercent"]!=58.3
            or not isinstance(trial["population"],str) or not trial["population"]):
        raise ValueError("Trial arms, treatment or active-control identity changed")
    arms=trial["doseArms"]
    if (not isinstance(arms,list) or len(arms)!=2
            or [(x.get("id"),x.get("randomized")) for x in arms]
            !=[("AFICAMTEN",88),("METOPROLOL",87)]
            or any(not isinstance(x,dict) or set(x)!={"id","randomized","dailyDose"}
                   or type(x["randomized"]) is not int
                   or not isinstance(x["dailyDose"],str) or not x["dailyDose"].strip()
                   for x in arms)):
        raise ValueError("175 randomized arms cannot be substituted or pooled")
    primary=record["primaryEndpoint"]
    keys(primary,{"id","classification","type","name","unit","aficamtenMeanChange",
                  "aficamten95CI","metoprololMeanChange","metoprolol95CI",
                  "adjustedBetweenGroupMeanDifference","adjustedBetweenGroup95CI",
                  "sourceReportedPValue","sourceRole","locator"},"pVO2 primary endpoint")
    fixed={
       "id":"PRIMARY_PEAK_VO2_CHANGE_WEEK24","classification":"PRIMARY",
       "type":"CONTINUOUS_CHANGE","unit":"mL/kg/min",
       "aficamtenMeanChange":1.1,"aficamten95CI":[0.5,1.7],
       "metoprololMeanChange":-1.2,"metoprolol95CI":[-1.7,-0.8],
       "adjustedBetweenGroupMeanDifference":2.3,"adjustedBetweenGroup95CI":[1.5,3.1],
       "sourceReportedPValue":"<0.001",
       "sourceRole":"ORIGINAL_PEER_REVIEWED_ABSTRACT"
    }
    if (any(type(primary.get(key)) is not type(val) or primary[key]!=val
            for key,val in fixed.items())
            or not isinstance(primary["name"],str) or not primary["name"]
            or not isinstance(primary["locator"],str) or "NEJM" not in primary["locator"]):
        raise ValueError("Original continuous exercise primary endpoint was modified")
    secondary=record["secondaryEndpoints"]
    if not isinstance(secondary,list) or len(secondary)!=len(EXPECTED_SECONDARY):
        raise ValueError("Six secondary effects are distinct and required")
    seen={}
    for item in secondary:
        keys(item,SECONDARY_FIELDS,"ACC summary secondary endpoint")
        ident=item["id"]
        if not isinstance(ident,str) or ident not in EXPECTED_SECONDARY or ident in seen:
            raise ValueError("Secondary endpoints changed or duplicated")
        expected=EXPECTED_SECONDARY[ident]
        actual=(item["type"],item["effect"],item["unit"],tuple(item["ci95"]),item["pValue"])
        if (actual!=expected
                or type(item["effect"]) not in (float,int)
                or item["reportedBy"]!="INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT"
                or not isinstance(item["name"],str) or not item["name"]):
            raise ValueError("ACC summary effect magnitude, unit, CI or source changed")
        seen[ident]=item
    if set(seen)!=set(EXPECTED_SECONDARY):
        raise ValueError("Incomplete summary evidence")
    safety=record["safety"]
    keys(safety,{"reportRole","seriousAdverseEvents","adverseEventDoseReductions",
                 "lvefBetweenGroupDifferencePercentagePoints","lvefDifference95CI",
                 "trialSummaryStatesSafetySimilar","oneDeathReportedInAficamtenArm",
                 "note"},"ACC safety")
    if (safety["reportRole"]!="INDEPENDENT_SOCIETY_SUMMARY_NOT_ORIGINAL_STUDY_REPORT"
            or safety["seriousAdverseEvents"]!={"aficamten":7,"metoprolol":6,
                                               "aficamtenDenom":88,"metoprololDenom":87}
            or safety["adverseEventDoseReductions"]!={"aficamten":1,"metoprolol":4}
            or safety["lvefBetweenGroupDifferencePercentagePoints"]!=-4.2
            or safety["lvefDifference95CI"]!=[-5.3,-3.1]
            or safety["trialSummaryStatesSafetySimilar"] is not True
            or safety["oneDeathReportedInAficamtenArm"] is not True
            or not isinstance(safety["note"],str) or len(safety["note"])<20):
        raise ValueError("Important cardiac safety observations missing or altered")
    for key in ("evidenceLimitationsUnreviewed","reviewQuestions"):
        rows=record[key]
        if (not isinstance(rows,list) or len(rows)<7 or len(rows)>50
                or any(not isinstance(x,str) or not 20 <=len(x)<=700 for x in rows)):
            raise ValueError("Unreviewed source limitations must be explicit")
    return {
        "nct":"NCT05767346",
        "status":"ORIGINAL_ABSTRACT_AND_SECONDARY_SUMMARY_UNREVIEWED_NOT_ADJUDICATED",
        "sourceUrl":NEJM,
        "secondarySourceUrl":ACC,
        "publishedDate":"2025-08-30",
        "outcomeExposedNotBlind":True,
        "endpointDataType":"CONTINUOUS_EXERCISE_CAPACITY_NOT_BINARY_ABSTINENCE",
        "primaryEndpointReported":primary.copy(),
        "secondaryEndpointsFromACC":list(seen[k].copy() for k in EXPECTED_SECONDARY),
        "publishedSafetyObservationFromACC":safety.copy(),
        "studyDesign":trial.copy(),
        "documentedLimitationsUnreviewed":record["evidenceLimitationsUnreviewed"][:],
        "independentReviewQuestions":record["reviewQuestions"][:],
        "sourceIndependentlyAuthenticated":False,
        "scientificallyAdjudicated":False,
        "actualOriginalSourceAuthenticationCount":0,
        "independentScientificReviews":0,
        "approvalProbability":None,
        "fdaOutcomeJudgment":None,
        "scientificScores":None,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=INPUT)
    args=parser.parse_args()
    print(json.dumps(assess(json.loads(args.source.read_text(encoding="utf-8"))),
                     indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
