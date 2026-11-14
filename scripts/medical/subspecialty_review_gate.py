#!/usr/bin/env python3
"""Fail-closed sole-owner specialty review gate; never authors clinical findings."""
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

def validate(dossier):
    errors = []
    if not dossier.get("nct") or not dossier.get("registrySourceSha256"):
        errors.append("MISSING_REGISTRY_PROVENANCE")
    if dossier.get("routingStatus") != "PROVISIONAL_SINGLE_SPECIALTY" or len(dossier.get("specialtyCandidates", [])) != 1:
        errors.append("SPECIALTY_NOT_RESOLVED")
    dimensions = dossier.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        return {"accepted": False, "errors": errors + ["INCOMPLETE_DIMENSION_SET"], "scientificAccuracyVerified": False}
    for name, dimension in dimensions.items():
        if dimension.get("status") != "REVIEWED":
            errors.append(name + ":NOT_REVIEWED")
        if not dimension.get("clinicalFinding") or not dimension.get("limitations"):
            errors.append(name + ":MISSING_FINDING_OR_LIMITATIONS")
        citations = dimension.get("sourceCitations")
        if not isinstance(citations, list) or not citations or any(
            not isinstance(c, dict) or not all(c.get(k) for k in ("sourceUrl", "sourceDate", "locator", "claim"))
            for c in citations
        ):
            errors.append(name + ":INVALID_CITATIONS")
        # The owner alone checks the specialist research dimensions. Older
        # independentReview/reviewer fields are ignored, never a gate.
        if dimension.get("ownerReviewStatus") != "OWNER_ACCEPTED_WITH_LIMITATIONS":
            errors.append(name + ":OWNER_REVIEW_NOT_ACCEPTED")
    if dossier.get("outcomePrediction") is not None or dossier.get("timingPrediction") is not None:
        errors.append("PREDICTION_NOT_PERMITTED_IN_SPECIALTY_DOSSIER")
    return {"accepted": not errors, "errors": errors,
            "status": "OWNER_SPECIALTY_REVIEW_STRUCTURE_ONLY" if not errors else "OWNER_REVIEW_REQUIRED",
            "ownerOnly": True,
            "externalReviewersRequired": 0,
            "externalSignoffsRequired": 0,
            "scientificAccuracyVerified": False}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("dossier", type=Path)
    args = p.parse_args()
    result = validate(json.loads(args.dossier.read_text()))
    print(json.dumps(result, indent=2))
    if not result["accepted"]:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
