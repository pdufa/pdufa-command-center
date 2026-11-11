#!/usr/bin/env python3
"""Generate a deterministic, unverified evidence-review worklist for FOCUS trials.

This file does not fetch evidence, score trials, or infer FDA outcomes.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "new-platform/frontend/data/p3PostDataActive.json"


def make_worklist(document):
    records = document.get("records") if isinstance(document, dict) else None
    if not isinstance(records, list) or len(records) != 29:
        raise ValueError("Expected exactly 29 FOCUS records")
    worklist = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("FOCUS records must be objects")
        nct = record.get("nct")
        if not isinstance(nct, str) or not nct.startswith("NCT") or not nct[3:].isdigit() or nct in seen:
            raise ValueError("Invalid or duplicate trial identifier")
        seen.add(nct)
        worklist.append({
            "nct": nct,
            "ticker": record.get("ticker"),
            "clinical_trial_source": record.get("resultsUrl"),
            "regulatory_source": record.get("regulatoryUrl"),
            "evidence_status": "unverified",
            "required_checks": [
                "confirm_trial_identity_and_phase",
                "verify_primary_endpoint_and_statistical_results",
                "verify_safety_and_tolerability",
                "verify_regulatory_submission_and_fda_status",
                "record_document_date_and_primary_source",
                "blind_historical_outcome_before_prediction",
            ],
            "adjudication": None,
            "prediction": None,
            "verified_specialist_gates": 0,
        })
    return {"schema_version": 1, "status": "review_required", "verified_predictions": 0, "trials": worklist}


def main():
    print(json.dumps(make_worklist(json.loads(ROSTER.read_text(encoding="utf-8"))), indent=2))


if __name__ == "__main__":
    main()
