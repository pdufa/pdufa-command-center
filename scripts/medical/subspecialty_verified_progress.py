#!/usr/bin/env python3
"""Report verified specialist review completion without mistaking queue tasks for assessments."""
import argparse
import json
from pathlib import Path

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "subspecialty_review_gate", Path(__file__).with_name("subspecialty_review_gate.py"))
_gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gate)

def summarize(queue, submitted_reviews):
    items = queue.get("items", [])
    if queue.get("status") != "RESEARCH_QUEUE_NOT_CLINICAL_ASSESSMENTS" or len(items) != 232:
        raise ValueError("Expected 232 FOCUS specialist research tasks")
    keys = [(x["nct"], x["dimension"]) for x in items]
    if len(set(keys)) != 232 or len({k[0] for k in keys}) != 29:
        raise ValueError("Invalid FOCUS research task identities")
    reviews = submitted_reviews.get("dossiers", [])
    if not isinstance(reviews, list):
        raise ValueError("Invalid submitted reviews")
    review_by_nct = {}
    for dossier in reviews:
        nct = dossier.get("nct")
        if nct in review_by_nct or nct not in {k[0] for k in keys}:
            raise ValueError("Duplicate or out-of-roster reviewed NCT")
        review_by_nct[nct] = dossier
    accepted = {}
    rejected = {}
    for nct, dossier in review_by_nct.items():
        outcome = _gate.validate(dossier)
        if outcome["accepted"]:
            accepted[nct] = dossier
        else:
            rejected[nct] = outcome["errors"]
    completed = sum(1 for nct, dimension in keys if nct in accepted)
    return {"schemaVersion": 1, "status": "STRUCTURAL_REVIEW_PROGRESS_NOT_ACCURACY",
            "trialCount": 29, "totalDimensions": 232,
            "structurallyValidatedDimensions": completed,
            "dimensionsRemaining": 232 - completed,
            "structurallyValidatedDossiers": len(accepted),
            "dossiersRemaining": 29 - len(accepted),
            "rejectedReviewPackages": rejected,
            "scientificAccuracyVerified": False,
            "fdaPredictionsUpdated": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", type=Path, required=True)
    p.add_argument("--reviews", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = summarize(json.loads(a.queue.read_text()), json.loads(a.reviews.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"structurallyValidatedDimensions": result["structurallyValidatedDimensions"],
                      "dimensionsRemaining": result["dimensionsRemaining"]}))

if __name__ == "__main__":
    main()
