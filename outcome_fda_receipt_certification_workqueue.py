"""Turn known FDA receipt evidence gaps into a fail-closed certification work queue."""
from __future__ import annotations

from outcome_fda_receipt_boundary_gap_report import build_receipt_boundary_gap_report


def build_receipt_certification_workqueue() -> dict:
    report = build_receipt_boundary_gap_report()
    tasks = []
    for row in report["unlinked_actions"]:
        tasks.append({
            "application_id": row.get("application_key") or row.get("application_id"),
            "action_date": row.get("action_date"),
            "status": "NEEDS_FDA_RECEIPT_EVIDENCE",
            "fda_receipt_verified": False,
            "model_eligible": False,
            "evidence_gap": row,
        })
    return {
        "status": "RESEARCH_ONLY_NOT_CERTIFIED",
        "open_tasks": len(tasks),
        "tasks": tasks,
        "certified_review_cycles_added": 0,
        "prediction_accuracy_estimate": None,
    }
