"""OUTCOME research status from SCIENCE provenance, with mandatory abstention.

Not a production decision model or validated prediction probability.
"""
from research.fda_science_provenance_gate import bind_science_research_gate


def build_outcome_provenance_status(reconstruction, science_dossiers):
    science = bind_science_research_gate(reconstruction, science_dossiers)
    cases = []
    for row in science["cases"]:
        cases.append({
            "event_key": row["event_key"],
            "science_provenance_blockers": row["blockers"],
            "outcome_decision": "ABSTAIN",
            "approval_probability": None,
            "pass_fail_grade": None,
            "ready_for_analysis_grade": "NOT_READY",
            "reluctant_grade": "INSUFFICIENT_VERIFIED_EVIDENCE",
            "eligible_for_validated_accuracy": False,
            "eligible_for_trading_recommendation": False,
        })
    return {"research_only": True, "trading_authorized": False,
            "validated_predictions": 0, "cases": cases}
