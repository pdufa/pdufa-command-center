#!/usr/bin/env python3
"""Deterministic specialist research work queue; prioritization is not scientific scoring."""
import argparse
import json
from pathlib import Path

DIMENSION_ORDER = (
    "regulatory_precedent_and_uncertainties",
    "endpoint_validity_and_clinical_meaning",
    "magnitude_and_durability_of_benefit",
    "specialty_specific_safety",
    "current_standard_of_care_and_comparator",
    "population_generalizability",
    "disease_subtype_and_diagnostic_criteria",
    "unmet_need_and_alternatives",
)

def build(report):
    if report.get("status") != "EVIDENCE_GAPS_NOT_ASSESSMENTS" or report.get("trialCount") != 29:
        raise ValueError("Requires 29-trial unadjudicated gap inventory")
    trials = report.get("trials", [])
    if len(trials) != 29 or len({t["nct"] for t in trials}) != 29:
        raise ValueError("FOCUS trial population mismatch")
    tasks = []
    for trial in trials:
        missing = trial.get("needsAdditionalEvidence")
        if not isinstance(missing, list) or len(set(missing)) != len(missing) or any(x not in DIMENSION_ORDER for x in missing):
            raise ValueError("Invalid specialist dimension list")
        if trial.get("scientificAssessmentStatus") != "NOT_ADJUDICATED":
            raise ValueError("Cannot treat completed assessments as research gaps")
        for dimension in DIMENSION_ORDER:
            if dimension in missing:
                tasks.append({
                    "nct": trial["nct"], "dimension": dimension,
                    "specialtyCandidates": trial.get("specialtyCandidates", []),
                    "specialistRoutingRequired": trial.get("routingStatus") != "PROVISIONAL_SINGLE_SPECIALTY",
                    "status": "RESEARCH_REQUIRED", "sourceCitations": [],
                    "scientificFinding": None, "independentReviewer": None,
                    "priorityBasis": "FIXED_RESEARCH_SEQUENCE_NOT_CLINICAL_RISK_SCORE",
                })
    tasks.sort(key=lambda t: (DIMENSION_ORDER.index(t["dimension"]), t["nct"]))
    return {"schemaVersion": 1, "status": "RESEARCH_QUEUE_NOT_SCIENTIFIC_ASSESSMENTS",
            "trialCount": 29, "taskCount": len(tasks), "completedResearchTasks": 0,
            "remainingResearchTasks": len(tasks), "tasks": tasks}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gaps", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = build(json.loads(a.gaps.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"taskCount": result["taskCount"], "remainingResearchTasks": result["remainingResearchTasks"]}))

if __name__ == "__main__":
    main()
