#!/usr/bin/env python3
"""Extract traceable registered protocol fields from an original ClinicalTrials.gov v2 JSON packet.

This is source extraction, not medical adjudication. It never predicts FDA outcomes.
"""
import argparse
import hashlib
import json
from pathlib import Path

FIELDS = {
    "conditions": ("conditionsModule", "conditions"),
    "phase": ("designModule", "phases"),
    "allocation": ("designModule", "designInfo", "allocation"),
    "masking": ("designModule", "designInfo", "maskingInfo", "masking"),
    "enrollment": ("designModule", "enrollmentInfo"),
    "primaryEndpoints": ("outcomesModule", "primaryOutcomes"),
    "secondaryEndpoints": ("outcomesModule", "secondaryOutcomes"),
    "eligibility": ("eligibilityModule", "eligibilityCriteria"),
    "arms": ("armsInterventionsModule", "armGroups"),
    "studyOverallStatus": ("statusModule", "overallStatus"),
    "studyLastUpdatePosted": ("statusModule", "studyLastUpdatePostDateStruct", "date"),
}

def at(data, keys):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data

def extract(packet, expected_nct, raw_bytes):
    protocol = packet.get("protocolSection") if isinstance(packet, dict) else None
    actual = at(protocol, ("identificationModule", "nctId"))
    if actual != expected_nct:
        raise ValueError("Registry NCT mismatch: refusing cross-trial evidence")
    fields = {}
    for name, path in FIELDS.items():
        value = at(protocol, path)
        fields[name] = {"value": value, "status": "CAPTURED_UNREVIEWED" if value is not None else "NOT_IN_SOURCE",
                        "locator": "protocolSection." + ".".join(path)}
    return {
        "schemaVersion": 1, "nct": actual,
        "source": "https://clinicaltrials.gov/study/" + actual,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "status": "SOURCE_EXTRACTED_NOT_ADJUDICATED",
        "fields": fields,
        "pendingOriginalDocumentChecks": ["full_protocol", "statistical_analysis_plan",
                                          "amendments", "endpoint_multiplicity", "cross_source_reconciliation"],
        "fdaPrediction": None
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nct", required=True)
    parser.add_argument("--source-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.source_json.read_bytes()
    report = extract(json.loads(raw), args.nct, raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"nct": report["nct"], "status": report["status"]}))

if __name__ == "__main__":
    main()
