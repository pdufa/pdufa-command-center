#!/usr/bin/env python3
"""Create a reproducible specialist research work queue from FOCUS evidence gaps.

This is a research queue, not clinical review, outcome prediction or priority score.
"""
import argparse
import json
from pathlib import Path

DIMENSION_ORDER = (
    "disease_subtype_and_diagnostic_criteria",
    "current_standard_of_care_and_comparator",
    "endpoint_validity_and_clinical_meaning",
    "population_generalizability",
    "magnitude_and_durability_of_benefit",
    "specialty_specific_safety",
    "unmet_need_and_alternatives",
    "regulatory_precedent_and_uncertainties",
)

def build(report):
    trials = report.get("trials", [])
    if report.get("status") != "EVIDENCE_GAPS_NOT_ASSESSMENTS" or len(trials) != 29:
        raise ValueError("Expected 29 FOCUS gap records")
    if len({r["nct"] for r in trials}) != 29:
        raise ValueError("Duplicate NCT")
    items = []
    for trial in sorted(trials, key=lambda x: x["nct"]):
        missing = trial.get("needsAdditionalEvidence", [])
        leads = trial.get("registryLeadDimensions", [])
        if len(set(missing)) != len(missing) or len(set(leads)) != len(leads) or set(missing) & set(leads) or set(missing) | set(leads) != set(DIMENSION_ORDER):
            raise ValueError("Incomplete or overlapping evidence dimensions")
        for dimension in DIMENSION_ORDER:
            items.append({
                "nct": trial["nct"], "dimension": dimension,
                "specialtyCandidates": trial.get("specialtyCandidates", []),
                "specialtyRoutingStatus": trial.get("routingStatus"),
                "researchTask": "LOCATE_EXTERNAL_EVIDENCE" if dimension in missing else "REVIEW_REGISTRY_LEADS_AND_SUPPLEMENT",
                "researchStatus": "NOT_STARTED",
                "clinicalAssessmentStatus": "NOT_ADJUDICATED",
                "independentChallengeStatus": "NOT_COMPLETED",
                "sourceCitations": [],
                "reviewer": None, "independentReviewer": None,
            })
    return {"schemaVersion": 1, "status": "RESEARCH_QUEUE_NOT_CLINICAL_ASSESSMENTS",
            "trialCount": 29, "taskCount": len(items), "researchTasksCompleted": 0,
            "scientificAssessmentsCompleted": 0, "items": items}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gaps", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = build(json.loads(a.gaps.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"trialCount": result["trialCount"], "taskCount": result["taskCount"]}))

if __name__ == "__main__":
    main()
