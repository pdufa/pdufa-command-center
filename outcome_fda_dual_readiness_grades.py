"""Dual research-readiness gates for the selected FDA action sample.

Grades describe documented evidence coverage, not predictive accuracy.
A full prediction-readiness pass is impossible without an unbiased complete
application denominator and independently certified historical cycles.
"""
from __future__ import annotations
import json
from outcome_fda_receipt_boundary_gap_report import build_receipt_boundary_gap_report

def build_outcome_readiness_grades() -> dict:
    gap = build_receipt_boundary_gap_report()
    total = gap["selected_action_denominator"]
    structured = gap["structured_timeline_count"]
    missing = gap["unlinked_actions_count"]
    if total <= 0 or structured + missing != total:
        raise ValueError("Selected action sample has inconsistent denominators")
    certified = gap["independently_certified_review_cycles"]
    eligible = gap["model_eligible_records"]
    if certified < 0 or eligible < 0 or certified > structured or eligible > certified:
        raise ValueError("Model certification counts exceed supported evidence")
    documented_pct = round(100 * structured / total, 1)
    return {
        "schema_version": "outcome-dual-readiness-grades-v1",
        "dataset_role": "selected_research_sample_not_unbiased_cohort",
        "evidence_grade": {
            "label": "CONDITIONAL_RESEARCH_ONLY",
            "ready_for_full_cycle_analysis": False,
            "structured_timelines": structured,
            "selected_action_denominator": total,
            "documented_timeline_coverage_percent": documented_pct,
            "missing_exact_receipt_boundary_actions": missing,
            "interpretation": "Coverage of selected FDA action timelines, not accuracy or model readiness",
        },
        "prediction_grade": {
            "label": "NOT_READY",
            "ready_for_prediction_analysis": False,
            "complete_application_denominator_verified": False,
            "independently_certified_review_cycles": certified,
            "model_eligible_records": eligible,
            "historical_asof_source_certification_complete": False,
            "prediction_accuracy_estimate": None,
            "prediction_probability": None,
        },
        "required_next_evidence": [
            "Independently verify FDA receipt boundary for all open actions",
            "Verify full unbiased application denominator",
            "Independently certify review cycles and historical source availability",
            "Validate model calibration on held-out chronological data before any accuracy claim",
        ],
    }

if __name__ == "__main__":
    print(json.dumps(build_outcome_readiness_grades(), indent=2, sort_keys=True))
