"""Build a conservative FDA source-review queue from untrusted candidate metadata.

This module never authenticates a source or certifies an FDA decision.
"""
from __future__ import annotations
from collections import Counter
from datetime import date, datetime, timezone
from screen_fda_evidence import screen_candidate

def build_review_queue(rows):
    """Return review tasks and blocking issues without promoting any record."""
    tasks = []
    seen = set()
    for index, row in enumerate(rows):
        screened = screen_candidate(row)
        issues = list(screened["issues"])
        if not isinstance(row, dict):
            tasks.append({"row_index": index, "status": "QUARANTINED",
                          "issues": issues, "model_eligible": False})
            continue
        key = (row.get("application_id"), row.get("submission_id"), row.get("review_cycle"))
        if key in seen:
            issues.append("duplicate_review_cycle_identity")
        seen.add(key)
        try:
            action = date.fromisoformat(row["action_date"])
            retrieved = datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00"))
            if retrieved.tzinfo is None or retrieved.utcoffset() is None:
                issues.append("retrieval_timestamp_missing_timezone")
            elif retrieved.astimezone(timezone.utc).date() < action:
                issues.append("retrieval_precedes_action")
        except (KeyError, ValueError, TypeError, AttributeError):
            pass  # Existing screening records invalid dates.
        if row.get("document_sha256") is None:
            issues.append("source_bytes_not_hashed")
        tasks.append({
            "row_index": index,
            "application_id": row.get("application_id"),
            "submission_id": row.get("submission_id"),
            "review_cycle": row.get("review_cycle"),
            "status": "QUARANTINED" if issues else "AWAITING_INDEPENDENT_REVIEW",
            "issues": issues,
            "review_required": [
                "retrieve_and_hash_official_source_bytes",
                "verify_action_and_submission_against_document",
                "independently_adjudicate_review_cycle",
                "audit_cohort_denominator_and_missing_crls",
            ],
            "independently_verified": False,
            "model_eligible": False,
        })
    return {
        "total_candidates": len(tasks),
        "status_counts": dict(sorted(Counter(t["status"] for t in tasks).items())),
        "tasks": tasks,
        "verified_pass_count": 0,
        "verified_fail_count": 0,
        "model_eligible_count": 0,
        "warning": "Queue preparation is not source authentication or independent adjudication.",
    }
