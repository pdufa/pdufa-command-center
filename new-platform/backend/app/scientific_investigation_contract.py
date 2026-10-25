"""Proposed eight-layer, forty-assessment scientific investigation contract.

This module is additive and intentionally does not change the legacy six-domain
scorer, existing GEM JR/GEM FS/FA presets, or any production decision.
Evidence verification must be independent of source ingestion.
"""
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


# Analytical depth is a review-workflow specification, not a claim that an
# assessment has been completed or independently verified.
DEPTH_LEVELS = (
    ("identity", "Establish exact trial, indication, population and dates"),
    ("registry", "Inventory primary registry fields and missing inputs"),
    ("source", "Identify dated original documents and source locators"),
    ("methods", "Reconcile protocol, endpoints, populations and analysis methods"),
    ("quantitative", "Critically examine effect estimates, uncertainty and safety"),
    ("triangulation", "Compare independent publications and contradictory evidence"),
    ("regulatory", "Assess applicability of agency records and manufacturing evidence"),
    ("adjudication", "Document independent reviewer decisions and residual uncertainty"),
)
assert len(DEPTH_LEVELS) == 8

def investigation_plan() -> dict:
    """Return all 320 review tasks; every task starts pending and unscored."""
    return {
        "schemaVersion": "scientific-investigation-depth8-v1",
        "layers": len(LAYERS),
        "assessments": sum(len(fields) for fields in LAYERS.values()),
        "depthLevels": [
            {"level": i, "id": key, "objective": objective}
            for i, (key, objective) in enumerate(DEPTH_LEVELS, start=1)
        ],
        "tasks": [
            {
                "assessmentId": f"{layer}.{field}",
                "depthLevel": i,
                "depthId": depth_id,
                "status": "pending_independent_review",
                "independentlyVerified": False,
                "scientificScore": None,
            }
            for layer, fields in LAYERS.items()
            for field in fields
            for i, (depth_id, _) in enumerate(DEPTH_LEVELS, start=1)
        ],
        "completedTasks": 0,
        "requiredTasks": 320,
        "readyForScientificConclusion": False,
        "approvalProbability": None,
    }

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
