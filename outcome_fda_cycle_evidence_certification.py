"""Independent evidence certification gate for historical OUTCOME cohorts.

This gate is separate from cohort membership and never infers certification
from a claimed complete denominator or a retrospective FDA decision label.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CycleEvidence:
    application_id: str
    review_cycle: int
    fda_receipt_date: date | None
    fda_receipt_source: str | None
    decision_date: date | None
    decision_source: str | None
    feature_snapshot_date: date | None
    feature_source_published_at: date | None
    complete_cohort_source: str | None
    independently_reviewed: bool = False
    independent_reviewer_id: str | None = None
    independent_review_date: date | None = None
    independent_review_evidence: str | None = None


def audit_cycle_evidence(rows: list[CycleEvidence]) -> dict:
    """Fail closed; return missing evidence for each review cycle, not scores."""
    seen = set()
    results = []
    for row in rows:
        key = (row.application_id, row.review_cycle)
        missing = []
        if not row.application_id or row.review_cycle < 1 or key in seen:
            missing.append("valid_unique_application_review_cycle")
        seen.add(key)
        for field in (
            "fda_receipt_date", "fda_receipt_source", "decision_date",
            "decision_source", "feature_snapshot_date",
            "feature_source_published_at", "complete_cohort_source",
        ):
            if not getattr(row, field):
                missing.append(field)
        if not row.independently_reviewed:
            missing.append("independent_review")
        if not row.independent_reviewer_id or not row.independent_review_date or not row.independent_review_evidence:
            missing.append("independent_review_attestation")
        if row.independent_review_date and row.decision_date and row.independent_review_date < row.decision_date:
            missing.append("review_precedes_decision")
        if row.fda_receipt_date and row.decision_date and row.fda_receipt_date > row.decision_date:
            missing.append("receipt_precedes_decision")
        if row.feature_snapshot_date and row.decision_date and row.feature_snapshot_date >= row.decision_date:
            missing.append("snapshot_precedes_decision")
        if row.feature_source_published_at and row.feature_snapshot_date and row.feature_source_published_at > row.feature_snapshot_date:
            missing.append("source_published_by_snapshot")
        results.append({
            "application_id": row.application_id,
            "review_cycle": row.review_cycle,
            "certified": not missing,
            "missing_or_invalid": missing,
        })
    return {
        "status": "CERTIFIED" if rows and all(x["certified"] for x in results) else "NOT_CERTIFIED",
        "total": len(rows),
        "certified_count": sum(x["certified"] for x in results),
        "records": results,
        "prediction_accuracy_estimate": None,
    }
