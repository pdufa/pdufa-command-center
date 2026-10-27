"""Turn known FDA receipt evidence gaps into a fail-closed certification work queue."""
from __future__ import annotations

from outcome_fda_receipt_boundary_gap_report import build_receipt_boundary_gap_report


def build_receipt_certification_workqueue() -> dict:
    report = build_receipt_boundary_gap_report()
    tasks = []
    for row in report["unlinked_actions"]:
        evidence = row["evidence"]
        tasks.append({
            "task_id": f'{row["application_key"]}:{row["final_fda_action_date"]}',
            "next_required_document": evidence["next_evidence"],
            "original_fda_action_source": row["final_action_source_url"],
            "receipt_blocker": evidence["reason"],
            "priority": "BLOCKING_CERTIFICATION",
            "application_id": row["application_key"],
            "action_date": row["final_fda_action_date"],
            "status": "NEEDS_FDA_RECEIPT_EVIDENCE",
            "fda_receipt_verified": False,
            "model_eligible": False,
            "evidence_gap": row,
        })
    tasks.sort(key=lambda task: (task["action_date"], task["application_id"]))
    return {
        "status": "RESEARCH_ONLY_NOT_CERTIFIED",
        "open_tasks": len(tasks),
        "tasks": tasks,
        "certified_review_cycles_added": 0,
        "prediction_accuracy_estimate": None,
    }
