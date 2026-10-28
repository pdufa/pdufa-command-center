"""Conservative research-only eligibility for reconstructed historical inputs.

Passing the source screening gate does not certify a prospective prediction.
"""
from research.fda_reconstruction_leakage_audit import audit_reconstruction_leakage


def build_reconstruction_input_gate(reconstruction):
    audit = audit_reconstruction_leakage(reconstruction)
    results = []
    for row in audit["cases"]:
        blockers = ["ORIGINAL_PREDICTION_CUTOFF_NOT_AUTHENTICATED"]
        if row["excluded_observations"]:
            blockers.append("EVIDENCE_WITHHELD_PENDING_PROVENANCE")
        if not row["candidate_observations"]:
            blockers.append("NO_FULLY_VERIFIED_PREDECISION_SOURCES")
        results.append({
            "event_key": row["event_key"],
            "research_candidate_observations": len(row["candidate_observations"]),
            "excluded_observations": len(row["excluded_observations"]),
            "eligible_for_validated_prediction": False,
            "eligible_for_training": False,
            "blockers": blockers,
        })
    return {"research_only": True, "trading_authorized": False,
            "validated_prediction_inputs": 0, "cases": results}
