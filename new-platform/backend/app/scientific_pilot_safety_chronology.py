"""KEYNOTE-024 source-stratified original and later safety denominators.

Published percentages are checked against explicitly cited denominators for
2016, but no new safety rate is inferred from ClinicalTrials.gov registry AE
groups, which may include crossover/retreatment treatment courses. The
2019 follow-up is a separate analysis, not a correction to 2016 findings.
No trial scoring, writes, background tasks or FDA forecast.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

NCT = "NCT02142738"
ORIGINAL_PMID = "27718847"
FOLLOWUP_PMID = "30620668"
ORIGINAL_PAPER = "https://pubmed.ncbi.nlm.nih.gov/27718847/"
ORIGINAL_TABLE = "https://www.nejm.org/doi/full/10.1056/nejmoa1606774"
FOLLOWUP_PAPER = "https://pubmed.ncbi.nlm.nih.gov/30620668/"
REGISTRY_URL = "https://clinicaltrials.gov/study/NCT02142738"

# The 2016 as-treated population excludes a chemotherapy-assigned patient
# who never started trial treatment. It must not be replaced by ITT n=151.
_ORIGINAL = {
    "treatment_related_any_grade": {"pembrolizumab": 113, "chemotherapy": 135,
                                    "expectedPercent": [73.4, 90.0]},
    "treatment_related_grade_3_to_5": {"pembrolizumab": 41, "chemotherapy": 80,
                                       "expectedPercent": [26.6, 53.3]},
    "serious_treatment_related_any_grade": {"pembrolizumab": 33, "chemotherapy": 31,
                                            "expectedPercent": [21.4, 20.7]},
    "treatment_related_discontinuation_any_grade": {
        "pembrolizumab": 11, "chemotherapy": 16,
        "expectedPercent": [7.1, 10.7],
    },
    "treatment_related_death": {"pembrolizumab": 1, "chemotherapy": 3,
                                "expectedPercent": [0.6, 2.0]},
}


def _published_round(affected: int, at_risk: int, reported: float) -> bool:
    # All percentages are quoted to one decimal in the original table.
    # Accept only <=0.051 percentage-point rounding tolerance; never use
    # round(..., 1) because tie-to-even may differ across publications.
    return (type(affected) is int and type(at_risk) is int
            and 0 <= affected <= at_risk and at_risk > 0
            and type(reported) in (int, float)
            and abs(100.0 * affected / at_risk - reported) < 0.051)


def keynote024_safety_chronology(
    published: Mapping[str, Any],
    registry_audit: Mapping[str, Any],
) -> dict:
    """Create bounded provenance snapshots after exact trial/source checks."""
    if (not isinstance(published, Mapping) or not isinstance(registry_audit, Mapping)
        or published.get("nct_id") != NCT
        or registry_audit.get("nctId") != NCT
        or published.get("overall_score") is not None
        or published.get("fda_approval_probability") is not None
        or registry_audit.get("readOnly") is not True
        or registry_audit.get("scientificScore") is not None
        or registry_audit.get("fdaApprovalProbability") is not None
        or registry_audit.get("inputReadinessGradeChanged") is not False
        or registry_audit.get("reluctanceGradeChanged") is not False):
        raise ValueError("KEYNOTE-024 evidence identity or unscored-state mismatch")
    snapshots = published.get("analysis_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 3:
        raise ValueError("Expected exactly three historical published snapshots")
    initial = next((s for s in snapshots if isinstance(s, Mapping)
                    and s.get("analysis_id") == "keynote024_initial_2016"), None)
    five_year = next((s for s in snapshots if isinstance(s, Mapping)
                      and s.get("analysis_id") == "keynote024_five_year_2021"), None)
    pro = next((s for s in snapshots if isinstance(s, Mapping)
                and s.get("analysis_id") == "keynote024_pros_2017"), None)
    if (not isinstance(initial, Mapping) or not isinstance(five_year, Mapping)
        or not isinstance(pro, Mapping)
        or initial.get("nct_id") != NCT or initial.get("source_id") != ORIGINAL_PMID
        or initial.get("source_url") != ORIGINAL_PAPER
        or initial.get("data_cutoff_date") != "2016-05-09"
        or initial.get("arm_counts_randomized") != {
            "pembrolizumab": 154, "chemotherapy": 151,
        }
        or five_year.get("nct_id") != NCT
        or five_year.get("source_id") != "33872070"
        or pro.get("source_id") != "29129441"):
        raise ValueError("Original study efficacy or source identity mismatch")
    safety = initial.get("safety")
    if not isinstance(safety, Mapping):
        raise ValueError("Original as-treated safety data missing")
    grade3 = safety.get("treatment_related_adverse_events_grade_3_to_5_percent")
    anygrade = safety.get("treatment_related_adverse_events_any_grade_percent")
    if (grade3 != {"pembrolizumab": 26.6, "chemotherapy": 53.3}
        or anygrade != {"pembrolizumab": 73.4, "chemotherapy": 90.0}):
        raise ValueError("Original published safety percentages changed")
    group_info = registry_audit.get("registrySafety")
    if (not isinstance(group_info, Mapping)
        or group_info.get("sourceUrl") != REGISTRY_URL
        or group_info.get("randomizedArmComparisonValidated") is not False
        or group_info.get("publishedTreatmentRelatedAeRatesReconciled") is not False
        or group_info.get("missingGroupsDoNotImplyZeroEvents") is not True):
        raise ValueError("Registry event-group attribution unsafe")
    group_count = group_info.get("groupCount")
    groups = group_info.get("groups")
    if (type(group_count) is not int or not 0 <= group_count <= 24
        or not isinstance(groups, list) or len(groups) != group_count):
        raise ValueError("Registry event-group count missing/mismatched")

    as_treated = {"pembrolizumab": 154, "chemotherapy": 150}
    rows = []
    for classification, source in _ORIGINAL.items():
        n1, n2 = source["pembrolizumab"], source["chemotherapy"]
        p1, p2 = source["expectedPercent"]
        if not (_published_round(n1, 154, p1)
                and _published_round(n2, 150, p2)):
            raise ValueError("Published AE percentages not consistent with denominators")
        rows.append({
            "classification": classification,
            "pembrolizumab": {"affected": n1, "atRisk": 154, "reportedPercent": p1},
            "chemotherapy": {"affected": n2, "atRisk": 150, "reportedPercent": p2},
            "sourceUrl": ORIGINAL_TABLE,
            "sourceLocator": "Table 3: Adverse Events in the As-Treated Population",
            "treatmentRelated": True,
            "sourceReportedNotIndependentlyVerified": True,
        })

    return deepcopy({
        "nctId": NCT,
        "status": "published_safety_source_reconciliation_only",
        "original2016": {
            "analysisId": "keynote024_initial_2016",
            "publicationDate": "2016-10-08",
            "dataCutoffDate": "2016-05-09",
            "sourceUrl": ORIGINAL_TABLE,
            "sourcePubMed": ORIGINAL_PAPER,
            "randomized": {"pembrolizumab": 154, "chemotherapy": 151},
            "asTreated": as_treated,
            "unexposedChemotherapyRandomized": 1,
            "reportedTreatRelatedSafety": rows,
            "roundingArithmeticChecked": True,
            "patientLevelVerified": False,
            "clinicalSafetyAppraisalComplete": False,
        },
        "immuneMediated2016": {
            "sourceUrl": ORIGINAL_TABLE,
            "sourceLocator": "Original manuscript Table 3 and Adverse Events narrative",
            "causalityDefinition": "regardless_of_investigator_treatment_attribution",
            "anyGradePercent": {"pembrolizumab": 29.2, "chemotherapy": 4.7},
            "grade3to4Percent": {"pembrolizumab": 9.7, "chemotherapy": 0.7},
            "noGrade5ImmuneMediatedEventsReported": True,
            "notEquivalentToTreatmentRelatedAE": True,
        },
        "updated2019": {
            "sourceId": FOLLOWUP_PMID,
            "sourceUrl": FOLLOWUP_PAPER,
            "publicationDate": "2019-01-08",
            "analysisDataCutoff": "2017-07-10",
            "randomized": {"pembrolizumab": 154, "chemotherapy": 151},
            "reportedGrade3to5TreatmentRelatedPercent": {
                "pembrolizumab": 31.2, "chemotherapy": 53.3,
            },
            "reportedOnStudyCrossoverPatients": 82,
            "intentionToTreatOS": {"hazardRatio": 0.63, "ci95": [0.47, 0.86]},
            "twoStageCrossoverAdjustedOS": {
                "hazardRatio": 0.49, "ci95": [0.34, 0.69],
            },
            "crossoverAdjustedInterpretation": "model_based_sensitivity_not_randomized_estimate",
            "publishedAEAffectedCountsExtracted": False,
            "mustNotOverwriteOriginal2016": True,
        },
        "registryReconciliation": {
            "archivedGroupsObserved": group_count,
            "sourceUrl": REGISTRY_URL,
            "countsPooledAcrossTreatmentCourses": False,
            "registryAEGroupMatchesJournalTRAE": False,
            "registryUsesDistinctCategoriesAndPossibleCrossover": True,
            "publishedSafetyDenominatorsIdentified": True,
            "crossSystemAEReconciliationCompleted": False,
            "missingOriginalSapStillBlocking": True,
            "nextAction": "Verify original archived group populations/crossover exposure and original trial SAP before adjudicating full benefit-risk.",
        },
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "inputReadinessGradeChanged": False,
        "reluctanceGradeChanged": False,
        "readOnly": True,
        "tradingActionsEnabled": False,
    })
