#!/usr/bin/env python3
"""Produce honest per-trial specialty evidence gap inventory, never clinical conclusions."""
import argparse
import json
from pathlib import Path

def summarize(report):
    dossiers = report.get("dossiers", [])
    if report.get("status") != "UNREVIEWED_REGISTRY_EVIDENCE_LEADS" or len(dossiers) != 29:
        raise ValueError("Expected 29 FOCUS evidence-lead dossiers")
    if len({d["nct"] for d in dossiers}) != 29:
        raise ValueError("Duplicate trial identifiers")
    rows = []
    for dossier in dossiers:
        dimensions = dossier.get("dimensions", {})
        if len(dimensions) != 8:
            raise ValueError("Expected eight specialist dimensions")
        covered = [name for name, value in dimensions.items() if value.get("registryEvidenceLeads")]
        missing = [name for name in dimensions if name not in covered]
        rows.append({"nct": dossier["nct"], "routingStatus": dossier.get("routingStatus"),
                     "specialtyCandidates": dossier.get("specialtyCandidates", []),
                     "registryLeadDimensions": covered, "needsAdditionalEvidence": missing,
                     "scientificAssessmentStatus": "NOT_ADJUDICATED",
                     "independentReviewStatus": "NOT_COMPLETED"})
    return {"schemaVersion": 1, "status": "EVIDENCE_GAPS_NOT_ASSESSMENTS",
            "trialCount": 29, "scientificallyAdjudicated": 0,
            "dimensionsWithRegistryLeads": sum(len(r["registryLeadDimensions"]) for r in rows),
            "dimensionsNeedingAdditionalEvidence": sum(len(r["needsAdditionalEvidence"]) for r in rows),
            "trials": rows}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = summarize(json.loads(a.input.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"trialCount": 29, "dimensionsNeedingAdditionalEvidence": result["dimensionsNeedingAdditionalEvidence"]}))

if __name__ == "__main__":
    main()
