#!/usr/bin/env python3
"""Read-only Level 4 protocol evidence inventory; no clinical grading or predictions."""
import argparse
import json
from pathlib import Path

FIELDS = {
    "phase": ("designModule", "phases"),
    "allocation": ("designModule", "designInfo", "allocation"),
    "masking": ("designModule", "designInfo", "maskingInfo", "masking"),
    "enrollment": ("designModule", "enrollmentInfo", "count"),
    "primary_endpoints": ("outcomesModule", "primaryOutcomes"),
    "secondary_endpoints": ("outcomesModule", "secondaryOutcomes"),
    "eligibility": ("eligibilityModule", "eligibilityCriteria"),
    "arms": ("armsInterventionsModule", "armGroups"),
}
def get(obj, path):
    for key in path:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj

def audit(preview):
    rows = []
    for app in preview.get("applications", []):
        for nct in app.get("nctIds", []):
            sources = [s for s in app.get("sources", []) if nct in s.get("identifiers", [])]
            # Preview observations are abbreviated and are not a substitute for full protocol.
            captured = bool(sources)
            rows.append({
                "nct": nct, "ticker": app.get("ticker"),
                "application_id": app.get("id"),
                "registry_pointer_captured": captured,
                "level4_status": "REQUIRES_ORIGINAL_PROTOCOL_REVIEW",
                "required_checks": list(FIELDS) + [
                    "protocol_version", "statistical_analysis_plan",
                    "endpoint_multiplicity", "amendments", "cross_source_reconciliation"
                ],
                "limitations": "Source pointers alone do not establish endpoint validity or protocol adjudication.",
            })
    unique = sorted({r["nct"] for r in rows})
    return {
        "schemaVersion": 1, "assessmentLevel": 4,
        "status": "INVENTORY_ONLY_NOT_SCIENTIFICALLY_ADJUDICATED",
        "trialCount": len(unique), "applicationRows": len(rows),
        "completedProtocolReviews": 0, "trials": rows,
        "policy": "No RAAS, grades, FDA probabilities, or FOCUS roster changes."
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", default="new-platform/frontend/data/deepMedicalIntelligencePreview.json")
    parser.add_argument("--output", default="reports/deep-medical-intelligence/level4-protocol-audit.json")
    args = parser.parse_args()
    report = audit(json.loads(Path(args.preview).read_text()))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "trialCount", "completedProtocolReviews")}))

if __name__ == "__main__":
    main()
