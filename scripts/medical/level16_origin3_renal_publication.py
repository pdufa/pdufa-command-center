#!/usr/bin/env python3
"""Source-separated ORIGIN 3 IgA nephropathy Phase 3 renal efficacy research.

This code records ORIGINAL JOURNAL-REPORTED facts from a 2025 prespecified
interim analysis and an October 2026 final efficacy article about ONE trial.
It never imputes missing source data, certifies a reviewer, assigns an FDA
probability, or allows late outcomes to leak into blind historical backtests.
"""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/scientific-levels1-6/origin3-published-renal-evidence-20261114.json"
NCT = "NCT04716231"
INTERIM_NEJM = "https://www.nejm.org/doi/full/10.1056/NEJMoa2510198"
FINAL_NEJM = "https://www.nejm.org/doi/full/10.1056/NEJMoa2610103"


def keys(item, expected, label):
    if not isinstance(item, dict) or set(item) != set(expected):
        raise ValueError(label + ": missing or prohibited evidence/certification fields")


def unchanged(item, mapping, label):
    for name, expected in mapping.items():
        val = item.get(name)
        if type(val) is not type(expected) or val != expected:
            raise ValueError(label + ": changed published fact " + name)


def text_items(values, min_items):
    if (not isinstance(values, list) or len(values) < min_items
            or len(values) > 50 or any(
                not isinstance(x, str) or not 15 <= len(x) <= 700 for x in values)):
        raise ValueError("A phase-specific uncertainty/review question is missing")


def source_check(report, expected):
    keys(report["source"], set(expected) | {"locator", "independentlyAuthenticated"}, "journal source")
    unchanged(report["source"], expected, "source")
    if (report["source"]["independentlyAuthenticated"] is not False
            or not isinstance(report["source"]["locator"], str)
            or not report["source"]["locator"].strip()):
        raise ValueError("Original journal source not independently authenticated")


def assess(record):
    keys(record, {
        "schemaVersion", "kind", "nct", "trial", "sponsor", "drug",
        "indication", "evidenceCutoffDate", "studyContext", "reports",
        "scientificQuestions", "originalClinicalSourceAuthenticated",
        "genuineStatisticalReviewCompleted", "genuineDiseaseSpecialistReviewCompleted",
        "independentChallengeCompleted", "scientificAdjudicationCompleted",
        "fdaApplicationCycleVerified", "blindHistoricalPredictionPermitted",
        "scientificScore", "approvalProbability", "fdaOutcomeJudgment"
    }, "ORIGIN3 research")
    unchanged(record, {
        "schemaVersion": 1,
        "kind": "ORIGIN3_EXACT_NCT_PHASE_FIRST_PUBLICATION_SEQUENCE_RESEARCH_ONLY",
        "nct": NCT,
        "trial": "ORIGIN 3",
        "sponsor": "Vera Therapeutics",
        "drug": "atacicept",
        "indication": "IgA nephropathy",
        "evidenceCutoffDate": "2026-11-14",
    }, "trial identity")
    for key in (
        "originalClinicalSourceAuthenticated", "genuineStatisticalReviewCompleted",
        "genuineDiseaseSpecialistReviewCompleted", "independentChallengeCompleted",
        "scientificAdjudicationCompleted", "fdaApplicationCycleVerified",
        "blindHistoricalPredictionPermitted"
    ):
        if record[key] is not False:
            raise ValueError("Unreviewed ORIGIN 3 research cannot certify " + key)
    for key in ("scientificScore", "approvalProbability", "fdaOutcomeJudgment"):
        if record[key] is not None:
            raise ValueError("No scores, PDUFA forecasts or scientific approval")
    context = record["studyContext"]
    keys(context, {
        "registryPhaseUnreviewed", "multiPartRegistryWarning", "design", "dose",
        "backgroundTherapy", "comparator", "activeDiseasePopulation",
        "endpointSequence", "exactApplicationCycleVerified"
    }, "study and phase")
    unchanged(context, {
        "registryPhaseUnreviewed": ["PHASE3"],
        "design": "RANDOMIZED_DOUBLE_BLIND_PLACEBO_CONTROLLED",
        "dose": "atacicept 150 mg subcutaneously once weekly versus matched placebo",
        "comparator": "PLACEBO_ON_BACKGROUND_THERAPY",
        "endpointSequence": [
            "WEEK36_24H_UPCR_INTERIM_PRIMARY",
            "WEEK52_EGFR_CHANGE_FINAL_SECONDARY",
            "WEEK104_ANNUAL_EGFR_SLOPE_FINAL_SECONDARY"
        ],
        "exactApplicationCycleVerified": False,
    }, "phase-specific study")
    if (any(not isinstance(context[k], str) or len(context[k]) < 10 for k in
            ("multiPartRegistryWarning", "backgroundTherapy", "activeDiseasePopulation"))):
        raise ValueError("Phase 2b/Phase 3 distinction and population required")
    reports = record["reports"]
    if (not isinstance(reports, list) or len(reports) != 2
            or any(not isinstance(r, dict) for r in reports)):
        raise ValueError("Both separately dated original articles are required")
    interim, final = reports
    keys(interim, {
        "id", "type", "source", "denominator", "primary", "safety",
        "limitation", "independentlyReviewed"
    }, "interim")
    unchanged(interim, {
        "id": "INTERIM_2025",
        "type": "PRESPECIFIED_PHASE3_INTERIM_ANALYSIS",
        "independentlyReviewed": False,
    }, "interim identity")
    source_check(interim, {
        "url": INTERIM_NEJM,
        "pubmedUrl": "https://pubmed.ncbi.nlm.nih.gov/41196369/",
        "pmid": "41196369",
        "doi": "10.1056/NEJMoa2510198",
        "publishedOnline": "2025-11-06",
        "printedIssue": "2026-02-12",
        "title": "A Phase 3 Trial of Atacicept in Patients with IgA Nephropathy",
    })
    keys(interim["denominator"], {
        "prespecifiedInterimAnalysisTotal", "atacicept", "placebo", "label"
    }, "week36 cohort")
    unchanged(interim["denominator"], {
        "prespecifiedInterimAnalysisTotal": 203,
        "atacicept": 106, "placebo": 97,
        "label": "INTERIM_ANALYSIS_SUBSET_NOT_FULL_431_RANDOMIZED_COHORT",
    }, "week36 cohort")
    if 106 + 97 != 203:
        raise ValueError("Interim group denominators mismatch")
    keys(interim["primary"], {
        "id", "measure", "timeWeek", "classification", "metric",
        "ataciceptPercentReduction", "placeboPercentReduction",
        "publishedBetweenGroupDifferencePercentagePoints", "difference95CI",
        "publishedPValue", "locator"
    }, "interim primary endpoint")
    unchanged(interim["primary"], {
        "id": "WEEK36_24H_UPCR_INTERIM_PRIMARY",
        "measure": "24-hour urinary protein-to-creatinine ratio percentage change from baseline",
        "timeWeek": 36,
        "classification": "PRIMARY_INTERIM",
        "metric": "GEOMETRIC_MEAN_PERCENT_REDUCTION",
        "ataciceptPercentReduction": 45.7,
        "placeboPercentReduction": 6.8,
        "publishedBetweenGroupDifferencePercentagePoints": 41.8,
        "difference95CI": [28.9, 52.3],
        "publishedPValue": "<0.001",
        "locator": "NEJM abstract Results, prespecified week-36 proteinuria comparison",
    }, "week36 primary")
    # The 41.8 pp geometric-mean contrast is source reported; it must not be
    # naively replaced with 45.7 - 6.8, which is a different estimand.
    keys(interim["safety"], {
        "measure", "ataciceptPercent", "placeboPercent", "assessment"
    }, "week36 safety")
    unchanged(interim["safety"], {
        "measure": "Any adverse events in the interim analysis",
        "ataciceptPercent": 59.3, "placeboPercent": 50.0,
        "assessment": "PUBLICATION_REPORTED_NOT_CAUSALLY_ADJUDICATED",
    }, "interim safety")
    if not isinstance(interim["limitation"], str) or len(interim["limitation"]) < 30:
        raise ValueError("Interim surrogate and sample limitation required")

    keys(final, {
        "id", "type", "source", "denominator", "secondaryEfficacy",
        "progression", "safety", "limitation", "independentlyReviewed"
    }, "final analysis")
    unchanged(final, {
        "id": "FINAL_2026",
        "type": "FINAL_PRESPECIFIED_PHASE3_EGFR_EFFICACY_ANALYSIS",
        "independentlyReviewed": False,
    }, "final identity")
    source_check(final, {
        "url": FINAL_NEJM,
        "pubmedUrl": "https://pubmed.ncbi.nlm.nih.gov/42911181/",
        "pmid": "42911181",
        "doi": "10.1056/NEJMoa2610103",
        "publishedOnline": "2026-10-22",
        "title": "Atacicept in IgA Nephropathy — Phase 3 Trial Final Efficacy Analysis",
    })
    if not (date.fromisoformat(interim["source"]["publishedOnline"])
            < date.fromisoformat(final["source"]["publishedOnline"])
            <= date.fromisoformat(record["evidenceCutoffDate"])):
        raise ValueError("Later final-efficacy report improperly dated")
    keys(final["denominator"], {
        "randomized", "treatedTotal", "ataciceptTreated", "placeboTreated", "label"
    }, "final analysis population")
    unchanged(final["denominator"], {
        "randomized": 431, "treatedTotal": 428,
        "ataciceptTreated": 214, "placeboTreated": 214,
        "label": "FINAL_COHORT_DISTINCT_FROM_203_INTERIM_POPULATION",
    }, "final population")
    efficacy = final["secondaryEfficacy"]
    if not isinstance(efficacy, list) or len(efficacy) != 2:
        raise ValueError("Final eGFR change and slope must both remain")
    expected = [
        {
            "id": "WEEK52_EGFR_CHANGE_FINAL_SECONDARY",
            "classification": "PRESPECIFIED_SECONDARY",
            "measure": "eGFR change at week 52",
            "unit": "mL/min/1.73m²", "timeWeek": 52,
            "ataciceptMeanChange": -0.11, "atacicept95CI": [-1.44, 1.22],
            "placeboMeanChange": -5.69, "placebo95CI": [-7.04, -4.35],
            "reportedBetweenGroupDifference": 5.58, "difference95CI": [3.68, 7.48],
            "publishedPValue": "<0.001",
            "locator": "NEJM final analysis abstract Results, week 52 eGFR"
        },
        {
            "id": "WEEK104_ANNUAL_EGFR_SLOPE_FINAL_SECONDARY",
            "classification": "PRESPECIFIED_SECONDARY",
            "measure": "Annualized eGFR slope through week 104",
            "unit": "mL/min/1.73m²/year", "timeWeek": 104,
            "ataciceptMeanSlope": -0.60, "atacicept95CI": [-1.62, 0.41],
            "placeboMeanSlope": -5.60, "placebo95CI": [-6.64, -4.57],
            "reportedBetweenGroupDifference": 5.00, "difference95CI": [3.55, 6.45],
            "publishedPValue": "<0.001",
            "locator": "NEJM final analysis abstract Results, 104 week annualized eGFR slope"
        }
    ]
    for row, exp in zip(efficacy, expected):
        keys(row, set(exp), "exact final eGFR endpoint")
        unchanged(row, exp, "published eGFR endpoint")
    progression = final["progression"]
    keys(progression, {
        "id", "atacicept", "ataciceptPercent", "placebo", "placeboPercent",
        "hazardRatio", "hr95CI", "publishedPValue", "includedHardOutcomeObservation", "label"
    }, "disease progression")
    unchanged(progression, {
        "id": "COMPOSITE_KIDNEY_DISEASE_PROGRESSION",
        "atacicept": 11, "ataciceptPercent": 5.1,
        "placebo": 38, "placeboPercent": 17.8,
        "hazardRatio": 0.24, "hr95CI": [0.12, 0.48],
        "publishedPValue": "<0.001",
        "includedHardOutcomeObservation": "0 atacicept vs 7 placebo for dialysis, transplantation or death components",
        "label": "PUBLISHED_COMPOSITE_NOT_MORTALITY_ENDPOINT",
    }, "composite progression")
    safety = final["safety"]
    keys(safety, {
        "exposedAtacicept", "exposedPlacebo", "anyAdverseEvents",
        "seriousAdverseEventsPercent", "deathsReported", "assessment"
    }, "final safety")
    unchanged(safety, {
        "exposedAtacicept": 214, "exposedPlacebo": 214,
        "anyAdverseEvents": {
            "atacicept": 160, "ataciceptPercent": 74.8,
            "placebo": 167, "placeboPercent": 78.0
        },
        "seriousAdverseEventsPercent": {"atacicept": 7.0, "placebo": 15.4},
        "deathsReported": {"atacicept": 0, "placebo": 1},
        "assessment": "PUBLISHED_REPORT_NOT_CENTRAL_MEDICAL_ADJUDICATION"
    }, "final adverse events")
    if not isinstance(final["limitation"], str) or len(final["limitation"]) < 30:
        raise ValueError("Postcutoff historical prediction contamination warning required")
    text_items(record["scientificQuestions"], 8)
    return {
        "nct": NCT,
        "status": "TWO_DATED_JOURNAL_REPORTS_ONE_PHASE3_TRIAL_NOT_INDEPENDENTLY_REVIEWED",
        "outcomeExposedNotBlind": True,
        "interimSource": INTERIM_NEJM,
        "finalSource": FINAL_NEJM,
        "interimPublicationDate": "2025-11-06",
        "finalPublicationDate": "2026-10-22",
        "studyContext": context.copy(),
        "interimAnalysis": interim.copy(),
        "finalAnalysis": final.copy(),
        "interimAndFinalCohortsNotInterchangeable": True,
        "primaryUPCRIsNotEGFR": True,
        "finalEGFREndpointsAreSecondary": True,
        "fdaPredictionPermitted": False,
        "historicalBlindBacktestPermitted": False,
        "independentReviewQuestions": record["scientificQuestions"][:],
        "sourceIndependentlyAuthenticated": False,
        "scientificallyAdjudicated": False,
        "independentlyAdjudicatedLevels": 0,
        "score": None,
        "approvalProbability": None,
        "fdaOutcomeJudgment": None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=INPUT)
    args = parser.parse_args()
    record = json.loads(args.source.read_text(encoding="utf-8"))
    print(json.dumps(assess(record), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
