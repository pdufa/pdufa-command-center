#!/usr/bin/env python3
"""Conservative ORCA-2 publication findings for clinical Levels 3, 4 and 6.

This is an exact-source, publication-reported metadata extraction.
It is NOT primary-data verification, independent clinical review, a blind
historical forecast, FDA scoring, or a scientific signoff.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/scientific-levels1-6/orca2-publication-outcomes-20261114.json"
SOURCE_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/"
EXPECTED = {
    "PRIMARY_CYT6_W3_6": ("PRIMARY", "CYT6", "WEEKS_3_TO_6", 68, 269, 25.3, 12, 271, 4.4, 8.0, [3.9, 16.3], "<.001"),
    "PRIMARY_CYT12_W9_12": ("PRIMARY", "CYT12", "WEEKS_9_TO_12", 88, 270, 32.6, 19, 271, 7.0, 6.3, [3.7, 11.6], "<.001"),
    "SECONDARY_CYT6_W3_24": ("SECONDARY", "CYT6", "WEEKS_3_TO_24", 24, 269, 8.9, 7, 271, 2.6, 3.7, [1.5, 10.2], ".002"),
    "SECONDARY_CYT12_W9_24": ("SECONDARY", "CYT12", "WEEKS_9_TO_24", 57, 270, 21.1, 13, 271, 4.8, 5.3, [2.8, 11.1], "<.001"),
}
ENDPOINT_FIELDS = (
    "classification", "arm", "interval", "activeAbstinent", "activeRandomized", "activePct",
    "placeboAbstinent", "placeboRandomized", "placeboPct", "oddsRatioReported", "ci95Reported",
    "pValueReported",
)
ENVELOPE = {
    "schemaVersion", "kind", "nct", "studyCode", "evidenceCutoffDate", "source",
    "trial", "efficacy", "safety", "limitationsUnreviewed", "unresolvedQuestions",
    "sourceIndependentlyAuthenticated", "sourceReviewerApproved",
    "independentlyAdjudicatedLevels", "predictionAllowed", "approvalProbability", "fdaOutcomeJudgment",
}


def _keys(obj, keys, label):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ValueError(label + ": unrecognized or missing metadata fields")


def _real(val):
    if type(val) not in (int, float):
        raise ValueError("Expected numeric published observation")
    return val


def assess(document):
    """Return source-located RESEARCH ONLY questions, without outcome prediction."""
    _keys(document, ENVELOPE, "ORCA-2 publication envelope")
    if (type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or document["kind"] != "ORCA2_PUBLICATION_EVIDENCE_UNREVIEWED_NOT_FDA_PREDICTION"
            or document["nct"] != "NCT04576949"
            or document["studyCode"] != "ACH-CYT-03"
            or document["evidenceCutoffDate"] != "2026-11-14"):
        raise ValueError("ORCA-2 cohort/source cutoff mismatch")
    if (document["sourceIndependentlyAuthenticated"] is not False
            or document["sourceReviewerApproved"] is not False
            or document["independentlyAdjudicatedLevels"] != 0
            or type(document["independentlyAdjudicatedLevels"]) is not int
            or document["predictionAllowed"] is not False
            or document["approvalProbability"] is not None
            or document["fdaOutcomeJudgment"] is not None):
        raise ValueError("Publication metadata cannot claim scientific review or FDA forecasts")
    source = document["source"]
    _keys(source, {"url", "pmid", "doi", "publishedDate", "sourceLocator", "authenticity"}, "Journal source")
    if (source["url"] != SOURCE_URL or source["pmid"] != "37432430"
            or source["doi"] != "10.1001/jama.2023.10042"
            or source["publishedDate"] != "2023-07-11"
            or source["authenticity"] != "PUBLICATION_TEXT_OBSERVED_NOT_INDEPENDENTLY_ATTESTED"
            or not isinstance(source["sourceLocator"], str)):
        raise ValueError("Unexpected original journal source")
    trial = document["trial"]
    _keys(trial, {"design", "studyPhaseUnreviewed", "randomization", "sites", "randomized",
                  "arms", "allArmsBehavioralSupport", "primaryAnalysisRandomizedCount",
                  "followupWeek24Completed", "missingOutcomeTreatment", "biochemicalCriterion"}, "Trial")
    if (trial["design"] != "THREE_GROUP_RANDOMIZED_DOUBLE_BLIND_PLACEBO_CONTROLLED"
            or trial["studyPhaseUnreviewed"] != "PHASE3"
            or trial["randomized"] != 810 or type(trial["randomized"]) is not int
            or trial["sites"] != 17 or type(trial["sites"]) is not int
            or trial["primaryAnalysisRandomizedCount"] != 810
            or trial["followupWeek24Completed"] != 618
            or trial["allArmsBehavioralSupport"] is not True
            or trial["missingOutcomeTreatment"] != "MISSING_OUTCOME_COUNTED_AS_SMOKING_AS_DESCRIBED_BY_PUBLICATION"):
        raise ValueError("Published trial design, denominator or attrition evidence changed")
    if (not isinstance(trial["arms"], list) or
            [(x.get("id"), x.get("randomized")) for x in trial["arms"]]
            != [("CYT6", 269), ("CYT12", 270), ("PLACEBO", 271)]):
        raise ValueError("Trial arm identities and randomized denominators changed")
    for arm in trial["arms"]:
        _keys(arm, {"id", "randomized", "dose"}, "Treatment arm")
        if not isinstance(arm["dose"], str) or not arm["dose"].strip():
            raise ValueError("Treatment arm dosing missing")
    if 269 + 270 + 271 != trial["randomized"]:
        raise ValueError("Published arm totals inconsistent")
    efficacy = document["efficacy"]
    if not isinstance(efficacy, list) or len(efficacy) != 4:
        raise ValueError("Expected four original publication comparisons")
    found = {}
    for row in efficacy:
        _keys(row, {"id", "classification", "arm", "interval", "activeAbstinent",
                    "activeRandomized", "activePct", "placeboAbstinent", "placeboRandomized",
                    "placeboPct", "oddsRatioReported", "ci95Reported", "pValueReported", "locator"}, "Endpoint")
        rid = row["id"]
        if rid not in EXPECTED or rid in found:
            raise ValueError("Unknown or duplicated clinical endpoint")
        actual = tuple(row[key] for key in ENDPOINT_FIELDS)
        expected = EXPECTED[rid]
        if len(actual) != len(expected) or any(
                type(x) is not type(y) and not (
                    type(x) in (int, float) and type(y) in (int, float)
                ) or x != y
                for x, y in zip(actual, expected)):
            raise ValueError("Publication endpoint group, role or reported effect changed")
        if not isinstance(row["locator"], str) or "Table 2" not in row["locator"]:
            raise ValueError("Original paper comparison locator missing")
        # These are a rounded source-reported rate and exact-source OR, not a
        # newly calculated statistical result or adjusted trial inference.
        for count, total, pct in (
                (row["activeAbstinent"], row["activeRandomized"], row["activePct"]),
                (row["placeboAbstinent"], row["placeboRandomized"], row["placeboPct"])):
            if any(type(z) not in (int, float) for z in (count, total, pct)):
                raise ValueError("Non-numeric published rate")
            if not 0 <= count <= total or abs(100 * count / total - pct) >= 0.051:
                raise ValueError("Reported percentage does not match trial denominator")
        found[rid] = row
    if set(found) != set(EXPECTED):
        raise ValueError("Publication comparison missing")
    safety = document["safety"]
    _keys(safety, {"population", "cytisiniclineExposed", "placeboExposed",
                   "seriousAdverseEvents", "adverseEventDiscontinuations",
                   "treatmentRelatedSeriousAdverseEventsJudgedByInvestigators",
                   "oneDeathReportedInCyt6"}, "Safety")
    if (safety["population"] != "RECEIVED_AT_LEAST_ONE_STUDY_DOSE"
            or safety["cytisiniclineExposed"] != 539
            or safety["placeboExposed"] != 270
            or safety["oneDeathReportedInCyt6"] is not True):
        raise ValueError("Published safety denominator or report mismatch")
    for key, pair in (
        ("seriousAdverseEvents", (18, 3)),
        ("adverseEventDiscontinuations", (16, 4)),
        ("treatmentRelatedSeriousAdverseEventsJudgedByInvestigators", (0, 0)),
    ):
        item = safety[key]
        _keys(item, {"cytisinicline", "placebo", "locator"}, "Safety item")
        if (type(item["cytisinicline"]) is not int
                or type(item["placebo"]) is not int
                or (item["cytisinicline"], item["placebo"]) != pair
                or not isinstance(item["locator"], str)
                or not item["locator"].strip()):
            raise ValueError("Published safety outcome was altered")
    for key in ("limitationsUnreviewed", "unresolvedQuestions"):
        items = document[key]
        if (not isinstance(items, list) or len(items) < 5 or len(items) > 30
                or any(not isinstance(q, str) or not 15 <= len(q) <= 500 for q in items)):
            raise ValueError("Source limitations and questions must remain explicit")
    return {
        "nct": "NCT04576949",
        "status": "PUBLICATION_REPORTED_RESULTS_NOT_AUTHENTICATED_OR_INDEPENDENTLY_ADJUDICATED",
        "sourceUrl": SOURCE_URL,
        "publishedDate": "2023-07-11",
        "outcomeExposedNotBlind": True,
        "publishedEfficacyComparisons": [found[k].copy() for k in EXPECTED],
        "publishedSafetyObservation": safety.copy(),
        "studyDesign": trial.copy(),
        "documentedLimitationsUnreviewed": document["limitationsUnreviewed"][:],
        "independentReviewQuestions": document["unresolvedQuestions"][:],
        "levelReadiness": {
            "3": "SOURCE_REPORTED_EFFICACY_SAFETY_NOT_INDEPENDENTLY_RECONCILED",
            "4": "REPORTED_RANDOMIZED_TRIAL_DESIGN_NOT_SOURCE_ADJUDICATED",
            "6": "SMOKING_ABSTINENCE_ENDPOINT_RELEVANCE_NOT_SPECIALIST_ADJUDICATED"
        },
        "actualOriginalSourceAuthenticationCount": 0,
        "independentScientificReviews": 0,
        "scientificScores": None,
        "fdaOutcomeJudgment": None,
        "approvalProbability": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT)
    args = parser.parse_args()
    print(json.dumps(assess(json.loads(args.source.read_text(encoding="utf-8"))),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
