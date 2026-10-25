"""Proposed eight-layer, forty-assessment scientific investigation contract.

This module is additive and intentionally does not change the legacy six-domain
scorer, existing GEM JR/GEM FS/FA presets, or any production decision.
Evidence verification must be independent of source ingestion.
"""
from dataclasses import dataclass

LAYERS = {
    "trial_design": ("randomization", "comparator", "blinding", "sample_size_power", "protocol_endpoints"),
    "efficacy": ("primary_endpoint", "effect_size", "confidence_interval", "multiplicity", "clinical_meaning"),
    "safety": ("serious_adverse_events", "discontinuations", "mortality", "exposure", "benefit_risk"),
    "biological_rationale": ("mechanism", "target_validation", "biomarker", "translational_support", "resistance"),
    "statistical_integrity": ("missing_data", "interim_analysis", "subgroup_robustness", "sensitivity", "protocol_deviations"),
    "evidence_reproducibility": ("source_provenance", "independent_confirmation", "publication_consistency", "data_completeness", "auditability"),
    "regulatory": ("endpoint_acceptability", "agency_interactions", "precedent", "submission_completeness", "manufacturing_readiness"),
    "timeline_and_uncertainty": ("trial_chronology", "readout_timing", "filing_timing", "conflicting_evidence", "remaining_unknowns"),
}
assert len(LAYERS) == 8 and all(len(fields) == 5 for fields in LAYERS.values())

def readiness(evidence: dict) -> dict:
    """Readiness only, never approval probability or invented efficacy scores.

    Each assessment must have independent_verification=True, a source URL,
    and a review disposition of verified; a self-reported status is insufficient.
    """
    missing = []
    for layer, fields in LAYERS.items():
        for field in fields:
            key = f"{layer}.{field}"
            item = evidence.get(key)
            if not (isinstance(item, dict)
                    and item.get("independent_verification") is True
                    and item.get("review_status") == "verified"
                    and isinstance(item.get("source_url"), str)
                    and item["source_url"].startswith(("https://", "http://"))):
                missing.append(key)
    total = 40
    verified = total - len(missing)
    return {
        "ready_for_analysis": not missing,
        "verified_assessments": verified,
        "required_assessments": total,
        "coverage_percent": round(100 * verified / total, 1),
        "unverified": missing,
        "scientific_score": None,
        "approval_probability": None,
        "status": "ready" if not missing else "insufficient_verified_evidence",
    }
