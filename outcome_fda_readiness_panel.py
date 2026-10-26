"""UI-neutral, read-only OUTCOME readiness panel payload.

Presentation consumers can render the two grades and a collapsible secondary
blocker list. This module cannot enable prediction, scoring or model training.
"""
from __future__ import annotations
import json
from outcome_fda_dual_readiness_grades import build_outcome_readiness_grades

BLOCKER_LABELS = {
    "unresolved_fda_receipt_boundaries": "Unresolved FDA receipt boundaries",
    "complete_unbiased_application_denominator_unverified": "Complete unbiased application denominator unverified",
    "uncertified_structured_review_cycles": "Structured review cycles not independently certified",
    "no_historical_source_publication_certification": "Historical source publication dates not certified",
    "no_held_out_chronological_calibration": "Held-out chronological calibration unavailable",
}

def build_outcome_readiness_panel() -> dict:
    grades = build_outcome_readiness_grades()
    evidence = grades["evidence_grade"]
    prediction = grades["prediction_grade"]
    manifest = grades["blocking_gate_manifest"]
    if manifest["all_prediction_gates_passed"] or prediction["ready_for_prediction_analysis"]:
        raise ValueError("This research-only readiness panel cannot authorize prediction")
    blockers = manifest["blocking_conditions"]
    if set(blockers) != set(BLOCKER_LABELS):
        raise ValueError("Unexpected or missing readiness gate")
    detail_rows = [
        {"key": key, "label": BLOCKER_LABELS[key], "blocking": bool(blockers[key]),
         "affected_count": value if type(value) is int else None}
        for key, value in blockers.items()
    ]
    if sum(row["blocking"] for row in detail_rows) != manifest["blocking_condition_count"]:
        raise ValueError("Blocker summary and detail counts disagree")
    return {
        "schema_version": "outcome-readiness-panel-v1",
        "display_role": "research_status_only",
        "primary": {
            "evidence_grade": evidence["label"],
            "documented_timeline_coverage_percent": evidence["documented_timeline_coverage_percent"],
            "documented_timeline_numerator": evidence["structured_timelines"],
            "selected_action_denominator": evidence["selected_action_denominator"],
            "prediction_grade": prediction["label"],
            "prediction_ready": False,
            "prediction_probability": None,
            "prediction_accuracy_estimate": None,
        },
        "secondary": {
            "collapsible": True,
            "initially_collapsed": True,
            "title": "Why prediction is not ready",
            "blocking_condition_count": manifest["blocking_condition_count"],
            "blocking_conditions": detail_rows,
        },
        "disclaimer": "85% is selected-sample evidence coverage, not accuracy, approval likelihood, or full-cohort completeness.",
    }

if __name__ == "__main__":
    print(json.dumps(build_outcome_readiness_panel(), indent=2, sort_keys=True))
