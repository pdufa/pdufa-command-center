#!/usr/bin/env python3
"""Phase-first readiness triage of retrieved ClinicalTrials.gov metadata.

Never treats a completed study, posted results, or Phase 3 as FDA approval.
"""
import json
import sys
from pathlib import Path

PHASES = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"}


def triage(collection):
    trials = collection.get("trials") if isinstance(collection, dict) else None
    if not isinstance(trials, list) or len(trials) != 29:
        raise ValueError("Expected 29 retrieved FOCUS trial entries")
    seen = set()
    output = []
    for trial in trials:
        if not isinstance(trial, dict):
            raise ValueError("Invalid trial entry")
        nct = trial.get("nct")
        if not isinstance(nct, str) or nct in seen:
            raise ValueError("Missing or duplicate trial identifier")
        seen.add(nct)
        if trial.get("status") != "retrieved":
            output.append({"nct": nct, "readiness": "retrieval_failed", "next_check": "retry_primary_source", "verified": False})
            continue
        phases = trial.get("phase")
        if not isinstance(phases, list) or not phases or any(p not in PHASES for p in phases):
            readiness, next_check = "phase_unresolved", "confirm_phase_in_primary_record"
        elif "PHASE3" in phases or "PHASE4" in phases:
            if trial.get("results_submitted") is True:
                readiness, next_check = "phase_appropriate_results_present", "independently_review_endpoints_and_safety"
            else:
                readiness, next_check = "phase_appropriate_results_missing", "locate_primary_readout_or_publication"
        else:
            readiness, next_check = "earlier_phase", "review_only_phase_appropriate_evidence"
        output.append({"nct": nct, "readiness": readiness, "next_check": next_check,
                       "verified": False, "prediction": None})
    return {"status": "triage_only", "verified_scientific_adjudications": 0, "trials": output}


def main():
    payload = json.load(sys.stdin)
    print(json.dumps(triage(payload), indent=2))


if __name__ == "__main__":
    main()
