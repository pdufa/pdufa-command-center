#!/usr/bin/env python3
"""Create owner-only, source-traceable specialty dossier shells from FOCUS readiness.

No invented specialist findings, efficacy conclusions, or FDA predictions.
"""
import argparse
import json
from pathlib import Path

DIMENSIONS = (
    "disease_subtype_and_diagnostic_criteria",
    "current_standard_of_care_and_comparator",
    "endpoint_validity_and_clinical_meaning",
    "population_generalizability",
    "magnitude_and_durability_of_benefit",
    "specialty_specific_safety",
    "unmet_need_and_alternatives",
    "regulatory_precedent_and_uncertainties",
)

def build(matrix):
    trials = matrix.get("trials", [])
    if matrix.get("status") != "EVIDENCE_READINESS_ONLY" or len(trials) != 29:
        raise ValueError("Expected original 29-trial evidence-readiness matrix")
    seen = set()
    dossiers = []
    for trial in trials:
        nct = trial["nct"]
        if nct in seen:
            raise ValueError("Duplicate NCT")
        seen.add(nct)
        routing = trial.get("subspecialty", {})
        candidates = routing.get("specialtyCandidates", [])
        source = trial.get("source")
        sha = routing.get("sourceSha256")
        conditions = routing.get("registryConditions", [])
        if candidates and (not source or not sha or not conditions):
            raise ValueError("Specialty candidates without traceable registry evidence")
        dimensions = {name: {
            "status": "EVIDENCE_REQUIRED",
            "sourceCitations": [],
            "clinicalFinding": None,
            "ownerReviewStatus": "OWNER_NOT_REVIEWED",
            "externalReviewerRequired": False,
        } for name in DIMENSIONS}
        dossiers.append({
            "nct": nct,
            "specialtyCandidates": candidates,
            "routingStatus": routing.get("routingStatus", "REQUIRES_SPECIALIST_REVIEW"),
            "registryConditions": conditions,
            "registrySource": source if conditions else None,
            "registrySourceSha256": sha if conditions else None,
            "registryLocator": routing.get("sourceLocator"),
            "dimensions": dimensions,
            "dossierStatus": "OWNER_NOT_REVIEWED",
            "outcomePrediction": None,
            "timingPrediction": None,
        })
    return {"schemaVersion": 1, "status": "DOSSIER_SHELLS_ONLY",
            "trialCount": len(dossiers), "scientificallyAdjudicated": 0,
            "ownerReviewedDossiers": 0,
            "externalReviewerRequirements": 0,
            "dossiers": dossiers}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = build(json.loads(args.matrix.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "trialCount": result["trialCount"]}))

if __name__ == "__main__":
    main()
