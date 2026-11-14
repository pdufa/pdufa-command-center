#!/usr/bin/env python3
"""ORCA-3 exact-NCT public JAMA clinical findings, research-only and unreviewed.

Paper-reported counts and CIs are frozen here to prevent accidental rewriting
or cross-trial substitution. This script does not authenticate original source
bytes, independently adjudicate efficacy/safety, sign a review or forecast FDA.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/scientific-levels1-6/orca3-publication-outcomes-20261114.json"
SOURCE_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC12012700/"
# Types and labels are deliberately strict: primary and secondary periods are
# different hypotheses, and the two distinct study arms are not pooled.
EXPECTED = {
 "PRIMARY_CYT6_W3_6": ("PRIMARY","CYT6","WEEKS_3_TO_6",39,263,14.8,16,265,6.0,2.9,(1.5,5.6),"<.001"),
 "PRIMARY_CYT12_W9_12": ("PRIMARY","CYT12","WEEKS_9_TO_12",80,264,30.3,25,265,9.4,4.4,(2.6,7.3),"<.001"),
 "SECONDARY_CYT6_W3_24": ("SECONDARY","CYT6","WEEKS_3_TO_24",18,263,6.8,3,265,1.1,6.3,(1.9,34.6),"<.001"),
 "SECONDARY_CYT12_W9_24": ("SECONDARY","CYT12","WEEKS_9_TO_24",54,264,20.5,11,265,4.2,5.8,(2.9,12.5),"<.001"),
}
EXPECTED_DISCREPANCIES = {
 ("SECONDARY_CYT6_W3_24","reported95ciLower","1.9","1.8"),
 ("SECONDARY_CYT12_W9_24","reported95ciUpper","12.5","12.4"),
}
ENDPOINT_KEYS = ("type","arm","period","activeCount","activeDenom","activePercent",
                 "placeboCount","placeboDenom","placeboPercent","publishedOddsRatio",
                 "table95ci","publishedPValue")
TOP_KEYS = {"schemaVersion","kind","nct","studyCode","evidenceCutoffDate","source","trial",
            "endpoints","sourceTextDiscrepanciesUnreviewed","safety","limitationsAndReviewNeeds",
            "sourceIndependentlyAuthenticated","independentMedicalReviewCompleted",
            "statisticallyAdjudicated","independentChallengeCompleted",
            "fdaApplicationLinkVerified","approvalProbability","approvalPrediction"}


def exact_keys(record, keys):
    if not isinstance(record, dict) or set(record) != set(keys):
        raise ValueError("Unexpected or missing ORCA-3 evidence/review fields")


def assess(document):
    exact_keys(document, TOP_KEYS)
    if (type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or document["kind"] != "ORCA3_PUBLICATION_RESULTS_RESEARCH_ONLY_NOT_ADJUDICATED"
            or document["nct"] != "NCT05206370" or document["studyCode"] != "ORCA-3"
            or document["evidenceCutoffDate"] != "2026-11-14"):
        raise ValueError("Wrong ORCA-3 scientific research identity or cutoff")
    for key in ("sourceIndependentlyAuthenticated","independentMedicalReviewCompleted",
                "statisticallyAdjudicated","independentChallengeCompleted",
                "fdaApplicationLinkVerified"):
        if document[key] is not False:
            raise ValueError("Unreviewed public paper cannot certify " + key)
    if document["approvalProbability"] is not None or document["approvalPrediction"] is not None:
        raise ValueError("Unreviewed source data cannot create an FDA forecast")
    source = document["source"]
    exact_keys(source, {"url","pmid","doi","publicationDate","paper","sourceLocator",
                        "authenticationStatus"})
    if (source["url"] != SOURCE_URL or source["pmid"] != "40257755"
            or source["doi"] != "10.1001/jamainternmed.2025.0628"
            or source["publicationDate"] != "2025-04-21"
            or source["paper"] != "JAMA Internal Medicine"
            or source["authenticationStatus"] != "PUBLIC_ARTICLE_TEXT_NOT_INDEPENDENTLY_AUTHENTICATED"
            or not isinstance(source["sourceLocator"], str) or not source["sourceLocator"]):
        raise ValueError("ORCA-3 article identity/provenance mismatch")
    trial = document["trial"]
    exact_keys(trial, {"registryPhaseUnreviewed","design","clinicalSites","randomized","arms",
                       "week24Completed","behavioralSupportAllArms","followupWeeks",
                       "safetyTreated","safetyArms","quitEndpoint","missingData"})
    if (trial["registryPhaseUnreviewed"] != ["PHASE3"]
            or trial["design"] != "THREE_ARM_RANDOMIZED_DOUBLE_BLIND_PLACEBO_CONTROLLED"
            or type(trial["clinicalSites"]) is not int or trial["clinicalSites"] != 20
            or type(trial["randomized"]) is not int or trial["randomized"] != 792
            or type(trial["week24Completed"]) is not int or trial["week24Completed"] != 628
            or trial["behavioralSupportAllArms"] is not True
            or type(trial["followupWeeks"]) is not int or trial["followupWeeks"] != 24
            or type(trial["safetyTreated"]) is not int or trial["safetyTreated"] != 785
            or trial["quitEndpoint"] != "CO_VERIFIED_CONTINUOUS_SMOKING_ABSTINENCE_CO_LT_10_PPM"
            or trial["missingData"] != "MISSING_SMOKING_OUTCOME_CLASSIFIED_SMOKING_PER_PUBLICATION"):
        raise ValueError("ORCA-3 population/phase/followup source facts changed")
    for key, expected in (
        ("arms", [("CYT6",263),("CYT12",264),("PLACEBO",265)]),
        ("safetyArms", [("CYT6",263),("CYT12",260),("PLACEBO",262)]),
    ):
        if (not isinstance(trial[key], list) or
                any(not isinstance(x, dict) or set(x) != {"id","n"}
                    or type(x["n"]) is not int for x in trial[key])
                or [(x["id"],x["n"]) for x in trial[key]] != expected):
            raise ValueError("Original randomized vs treated arm denominators changed")
    if sum(x["n"] for x in trial["arms"]) != 792 or sum(x["n"] for x in trial["safetyArms"]) != 785:
        raise ValueError("Original trial arm totals do not reconcile")
    endpoints = document["endpoints"]
    if not isinstance(endpoints, list) or len(endpoints) != 4:
        raise ValueError("All four ORCA-3 primary and secondary outcomes are required")
    seen = {}
    for row in endpoints:
        exact_keys(row, {"id", *ENDPOINT_KEYS, "locator"})
        ident = row["id"]
        if not isinstance(ident, str) or ident not in EXPECTED or ident in seen:
            raise ValueError("Unexpected/duplicate endpoint")
        actual = tuple(
            tuple(row[x]) if x == "table95ci" and isinstance(row[x], list) else row[x]
            for x in ENDPOINT_KEYS
        )
        if actual != EXPECTED[ident]:
            raise ValueError("Published endpoint is substituted, misclassified, or changed")
        if any(type(row[x]) is not int for x in
               ("activeCount","activeDenom","placeboCount","placeboDenom")):
            raise ValueError("Original integer efficacy counts required")
        if (not isinstance(row["locator"], str) or
                "Table 2" not in row["locator"]):
            raise ValueError("Endpoint source locator missing")
        for cnt, denom, pct in (
            (row["activeCount"],row["activeDenom"],row["activePercent"]),
            (row["placeboCount"],row["placeboDenom"],row["placeboPercent"])
        ):
            if not 0 <= cnt <= denom or abs(100*cnt/denom-pct) >= 0.051:
                raise ValueError("Published percentage inconsistent with arm count")
        seen[ident] = row
    if set(seen) != set(EXPECTED):
        raise ValueError("Missing original comparison")
    discrepancies = document["sourceTextDiscrepanciesUnreviewed"]
    if not isinstance(discrepancies, list) or len(discrepancies) != 2:
        raise ValueError("Both source-text discrepancies must remain visible")
    found = set()
    for item in discrepancies:
        exact_keys(item, {"endpointId","field","table2","narrative","status"})
        current = (item["endpointId"],item["field"],item["table2"],item["narrative"])
        if (current not in EXPECTED_DISCREPANCIES or current in found
                or item["status"] != "ORIGINAL_ARTICLE_TABLE_VS_ABSTRACT_OR_RESULTS_TEXT_DISCREPANCY_REQUIRES_SOURCE_CHECK"):
            raise ValueError("Unresolved article/table CI discrepancy hidden or changed")
        found.add(current)
    if found != EXPECTED_DISCREPANCIES:
        raise ValueError("Discrepancy source observations missing")
    safety = document["safety"]
    exact_keys(safety, {"combinedCytisiniclineExposed","placeboExposed",
                        "seriousTreatmentEmergentAEs","seriousTreatmentRelatedAEsInvestigatorJudged",
                        "studyDrugDiscontinuationsDueToAEs","deathsInCytisiniclineArms",
                        "deathsJudgedUnrelatedOrUnlikelyByInvestigators",
                        "deathsPlaceboReportedInSafetyParagraph"})
    if (type(safety["combinedCytisiniclineExposed"]) is not int
            or safety["combinedCytisiniclineExposed"] != 523
            or type(safety["placeboExposed"]) is not int
            or safety["placeboExposed"] != 262
            or type(safety["deathsInCytisiniclineArms"]) is not int
            or safety["deathsInCytisiniclineArms"] != 4
            or type(safety["deathsJudgedUnrelatedOrUnlikelyByInvestigators"]) is not int
            or safety["deathsJudgedUnrelatedOrUnlikelyByInvestigators"] != 4
            or type(safety["deathsPlaceboReportedInSafetyParagraph"]) is not int
            or safety["deathsPlaceboReportedInSafetyParagraph"] != 0):
        raise ValueError("ORCA-3 serious safety data changed")
    for key, counts in (
        ("seriousTreatmentEmergentAEs",(16,8)),
        ("seriousTreatmentRelatedAEsInvestigatorJudged",(0,0)),
        ("studyDrugDiscontinuationsDueToAEs",(9,3))
    ):
        item = safety[key]
        exact_keys(item, {"cytisinicline","placebo","sourceLocator"})
        if (type(item["cytisinicline"]) is not int
                or type(item["placebo"]) is not int
                or (item["cytisinicline"],item["placebo"]) != counts
                or not isinstance(item["sourceLocator"], str)
                or not item["sourceLocator"]):
            raise ValueError("Published safety counts misreported")
    limitations = document["limitationsAndReviewNeeds"]
    if (not isinstance(limitations, list) or len(limitations) != 8
            or any(not isinstance(s,str) or not 20 <= len(s) <= 500 for s in limitations)):
        raise ValueError("Original ORCA-3 report limitations must be preserved")
    return {
        "nct":"NCT05206370",
        "status":"PUBLICATION_REPORTED_RESULTS_NOT_AUTHENTICATED_OR_INDEPENDENTLY_ADJUDICATED",
        "sourceUrl":SOURCE_URL,
        "publishedDate":"2025-04-21",
        "outcomeExposedNotBlind":True,
        "publishedEfficacyComparisons":[seen[k].copy() for k in EXPECTED],
        "publishedSafetyObservation":safety.copy(),
        "studyDesign":trial.copy(),
        "publicationTextDiscrepanciesUnreviewed":discrepancies[:],
        "documentedLimitationsUnreviewed":limitations[:],
        "independentReviewQuestions":[
            "Authenticate exact ORCA-3 original sources, registry/NCT, protocol and SAP history",
            "Reconcile the two minor Table 2 versus narrative confidence-interval differences",
            "Review efficacy in each prespecified primary and secondary family, including missing-as-smoking",
            "Review four deaths despite investigator assessment unrelated/unlikely to drug",
            "Reconcile phase, population, safety denominators, comparator, follow-up and clinical relevance",
            "Conduct qualified independent statistical and disease-specialist review; challenge and adjudicate"
        ],
        "levelReadiness":{
            "3":"PUBLISHED_EFFICACY_SAFETY_NOT_ADJUDICATED",
            "4":"PUBLISHED_RANDOMIZED_DESIGN_NOT_ADJUDICATED",
            "6":"SMOKING_CESSATION_ENDPOINT_SIGNIFICANCE_NOT_SPECIALIST_ADJUDICATED"
        },
        "actualOriginalSourceAuthenticationCount":0,
        "independentScientificReviews":0,
        "scientificScores":None,
        "fdaOutcomeJudgment":None,
        "approvalProbability":None,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=INPUT)
    args=parser.parse_args()
    print(json.dumps(assess(json.loads(args.source.read_text(encoding="utf-8"))),
                     indent=2,ensure_ascii=False))


if __name__=="__main__":
    main()
