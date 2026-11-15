"""Bind saved registry facts to the six-level contract without inventing reviews.

This is an evidence adapter, not a scientific scoring method. Regulatory outcome
caches and candidate grades are deliberately not inputs.
"""
from __future__ import annotations
import hashlib
import json

VERSION = "saved-registry-scientific-inventory-v1"


def attach_registry_inventory(level_one, levels, registry, *, trial_id, retrieved_at):
    if (level_one.get("executionStatus") != "INTAKE_ONLY"
            or registry.get("nct_id") != trial_id):
        return
    design = registry.get("study_design") or {}
    info = design.get("designInfo") if isinstance(design, dict) else {}
    info = info if isinstance(info, dict) else {}
    # Restrict to source fields; do not hash or expose outcomes from derived caches.
    fields = {key: registry.get(key) for key in (
        "nct_id", "phases", "status", "last_update_posted", "study_design",
        "primary_outcomes", "secondary_outcomes", "treatment_groups",
        "eligibility", "enrollment", "conditions", "has_results",
    )}
    digest = hashlib.sha256(json.dumps(fields, sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False, allow_nan=False).encode()).hexdigest()
    provenance = {
        "source": "https://clinicaltrials.gov/study/" + trial_id,
        "sourceDate": level_one["registrySourceDate"], "retrievedAt": retrieved_at,
        "documentType": "SAVED_REGISTRY_SUMMARY", "nctId": trial_id,
        "inputSha256": digest, "hashScope": "ALLOWLISTED_SAVED_SUMMARY_NOT_ORIGINAL_DOCUMENT",
        "sourceVerificationMethod": "AUTOMATED_IDENTITY_AND_CHRONOLOGY",
        "scientificValidation": "NOT_VERIFIED", "reviewerId": None,
        "reviewedAt": None, "rationale": None,
    }
    observations = {
        "2": {"randomizationAndControl": info.get("allocation"),
              "blindingAndBias": info.get("maskingInfo"),
              "populationAndEligibility": registry.get("eligibility"),
              "sampleSizeRationale": registry.get("enrollment")},
        "3": {"primaryEndpointResults": registry.get("primary_outcomes")},
        "4": {},
        "5": {"indicationDefinition": registry.get("conditions")},
        "6": {},
    }
    for number, level in levels.items():
        inventory = {}
        for criterion, state in level["criteria"].items():
            value = observations.get(number, {}).get(criterion)
            observed = value is not None and value != {} and value != [] and value != ""
            inventory[criterion] = {
                "state": "NOT_YET_EXPECTED" if state == "NOT_YET_EXPECTED" else
                         "AVAILABLE_NOT_REVIEWED" if observed else "NOT_ASSESSED",
                "observation": value if observed else None,
                "provenance": dict(provenance) if observed else None,
                "limitation": "Registry metadata does not establish protocol conduct, sample-size rationale, endpoint results, clinical benefit, safety or regulatory readiness.",
            }
        level["registryEvidenceInventory"] = inventory
        level["inventoryVersion"] = VERSION
