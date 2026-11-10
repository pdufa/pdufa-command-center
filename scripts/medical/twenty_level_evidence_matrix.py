#!/usr/bin/env python3
"""Create a read-only 20-level evidence readiness matrix from FOCUS registry checkpoints.

Presence of a registry field is NOT scientific assessment or FDA prediction.
"""
import argparse
import json
from pathlib import Path

from deep_clinical_subspecialty import route

# Level-specific registry pointers; levels without a reliable registry-only
# proxy deliberately have no pointers and require original external evidence.
POINTERS = {
    1: ["phase"], 2: ["phase"], 3: ["primaryEndpoints", "secondaryEndpoints"],
    4: ["allocation", "masking", "enrollment", "arms", "eligibility"],
    5: ["primaryEndpoints"], 6: ["primaryEndpoints"],
    7: ["eligibility", "enrollment"], 8: [],
    9: [], 10: [], 11: [], 12: [], 13: [], 14: [],
    15: [], 16: [], 17: [], 18: [], 19: [], 20: [],
}

def build(definition, checkpoint, roster):
    levels = definition["levels"]
    if [x["level"] for x in levels] != list(range(1, 21)):
        raise ValueError("20-level definition is incomplete or out of order")
    ncts = list(dict.fromkeys(x["nct"] for x in roster["records"]))
    if len(ncts) != 29:
        raise ValueError("Unexpected FOCUS population; refusing silent roster changes")
    records = checkpoint.get("results", {})
    rows = []
    for nct in ncts:
        result = records.get(nct, {})
        evidence = result.get("evidence", {}) if result.get("status") == "CAPTURED_UNREVIEWED" else {}
        if evidence and evidence.get("nct") != nct:
            raise ValueError("Cross-trial evidence in checkpoint")
        fields = evidence.get("fields", {})
        condition_field = fields.get("conditions", {})
        conditions = condition_field.get("value") if condition_field.get("status") == "CAPTURED_UNREVIEWED" else None
        if not isinstance(conditions, list):
            conditions = []
        specialty_routes = [route(c, nct) for c in conditions if isinstance(c, str)]
        candidates = sorted({specialty for item in specialty_routes for specialty in item["specialtyCandidates"]})
        specialty_status = ("PROVISIONAL_SINGLE_SPECIALTY" if len(candidates) == 1 and specialty_routes
                            and all(x["routingStatus"] == "PROVISIONAL_SINGLE_SPECIALTY" for x in specialty_routes)
                            else "REQUIRES_SPECIALIST_REVIEW")
        per_level = []
        for level in levels:
            required = POINTERS[level["level"]]
            present = [key for key in required if fields.get(key, {}).get("status") == "CAPTURED_UNREVIEWED"]
            per_level.append({
                "level": level["level"], "name": level["name"],
                "sourceFieldsPresent": present,
                "sourceFieldsMissing": [key for key in required if key not in present],
                "registryEvidenceStatus": ("PARTIAL_SOURCE_CAPTURE_NOT_REVIEWED" if present else
                                           "EXTERNAL_EVIDENCE_REQUIRED" if not required else
                                           "REGISTRY_FIELDS_MISSING"),
                "scientificReviewStatus": "NOT_ADJUDICATED",
                "decision": None, "probability": None
            })
        rows.append({"nct": nct, "source": evidence.get("source"), "levels": per_level,
                     "subspecialty": {"registryConditions": conditions,
                         "sourceLocator": condition_field.get("locator") if conditions else None,
                         "sourceSha256": evidence.get("sha256") if conditions else None,
                         "specialtyCandidates": candidates, "routingStatus": specialty_status,
                         "reviewDimensions": specialty_routes[0]["reviewDimensions"] if specialty_routes else [],
                         "scientificReviewStatus": "NOT_ADJUDICATED",
                         "specialistJudgment": None, "fdaOutcomePrediction": None,
                         "fdaTimingPrediction": None}})
    return {"schemaVersion": 1, "status": "EVIDENCE_READINESS_ONLY",
            "definitionKind": definition["kind"], "trialCount": len(rows),
            "scientificallyAdjudicatedTrials": 0, "calibratedProbabilities": 0,
            "trials": rows}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--definition", type=Path, default=Path("new-platform/frontend/data/deepMedicalTwentyLevelExpansion.json"))
    parser.add_argument("--roster", type=Path, default=Path("new-platform/frontend/data/p3PostDataActive.json"))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build(json.loads(args.definition.read_text()), json.loads(args.checkpoint.read_text()),
                   json.loads(args.roster.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "trialCount": report["trialCount"]}))

if __name__ == "__main__":
    main()
