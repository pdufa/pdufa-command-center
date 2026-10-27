"""FDA decision outcome taxonomy for application-level PDUFA evaluation.

This module classifies verified events, not clinical trials. Unknown and censored
outcomes are never forced into the binary PASS/FAIL training set.
"""
from __future__ import annotations
from datetime import date
from typing import Any, Mapping

APPROVAL_ACTIONS = {"approval", "accelerated_approval", "traditional_approval"}
NONAPPROVAL_ACTIONS = {"complete_response_letter", "crl"}
CENSORED_ACTIONS = {
    "withdrawn", "withdrawal", "delayed", "pending", "resubmitted",
    "refuse_to_file", "rtf", "tentative_approval", "administrative_extension",
}


def classify_decision(event: Mapping[str, Any], *, as_of: str) -> dict[str, Any]:
    """Classify only FDA actions independently documented by the as-of cutoff."""
    date.fromisoformat(as_of)
    application_id = str(event.get("application_id") or "").strip()
    source_url = str(event.get("source_url") or "").strip()
    raw_date = str(event.get("decision_date") or "").strip()
    action = str(event.get("action") or "").strip().lower().replace(" ", "_")
    base = {"application_id": application_id or None, "action": action or None,
            "label": None, "eligible_for_binary_training": False}
    if not application_id or not source_url or not raw_date:
        return {**base, "status": "insufficient_verified_evidence"}
    try:
        decision_date = date.fromisoformat(raw_date)
    except ValueError:
        return {**base, "status": "invalid_decision_date"}
    if decision_date > date.fromisoformat(as_of):
        return {**base, "status": "future_event_excluded"}
    if action in APPROVAL_ACTIONS:
        return {**base, "status": "verified_binary", "label": "PASS",
                "eligible_for_binary_training": True}
    if action in NONAPPROVAL_ACTIONS:
        return {**base, "status": "verified_binary", "label": "FAIL",
                "eligible_for_binary_training": True}
    if action in CENSORED_ACTIONS:
        return {**base, "status": "censored_or_out_of_scope"}
    return {**base, "status": "unknown_action_requires_review"}


def deduplicate_applications(events: list[Mapping[str, Any]], *, as_of: str) -> dict[str, Any]:
    """Do not treat multiple trials or repeated rows as independent decisions.

    Conflicting verified action labels for the same application are flagged for
    manual review, never silently resolved.
    """
    by_application: dict[str, list[dict[str, Any]]] = {}
    excluded = []
    for event in events:
        result = classify_decision(event, as_of=as_of)
        if result["status"] != "verified_binary":
            excluded.append(result)
            continue
        by_application.setdefault(result["application_id"], []).append(result)
    accepted, conflicts = [], []
    for application_id, rows in sorted(by_application.items()):
        labels = {row["label"] for row in rows}
        if len(labels) != 1:
            conflicts.append(application_id)
        else:
            accepted.append({"application_id": application_id, "label": rows[0]["label"]})
    return {"accepted": accepted, "conflicting_applications": conflicts,
            "excluded": excluded, "counts": {
                "verified_applications": len(accepted),
                "conflicting_applications": len(conflicts),
                "excluded_events": len(excluded)}}
