"""HOP outcome cohort quality checks; prevents biased CRL archive as denominator.

A historical decision must be sampled from a defined, complete application
cohort before its outcome is used to estimate an approval rate. CRL publication
alone does not establish a representative sample.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Iterable

@dataclass(frozen=True)
class OutcomeObservation:
    application_id: str
    review_cycle: int
    decision_date: date
    outcome: str
    ascertainment_source: str
    cohort_id: str
    public_features_as_of: date | None

OUTCOMES = {"APPROVED", "COMPLETE_RESPONSE"}
DENOMINATOR_SOURCES = {"COMPLETE_APPLICATION_COHORT"}

def audit_outcome_cohort(rows: Iterable[OutcomeObservation], as_of: date) -> dict:
    """Return auditable counts, not an approval probability."""
    counts = Counter()
    seen = set()
    cohort_ids = set()
    for row in rows:
        key = (row.application_id, row.review_cycle)
        if not row.application_id or row.review_cycle < 1 or key in seen:
            counts["invalid_or_duplicate"] += 1
            continue
        seen.add(key)
        if row.outcome not in OUTCOMES or row.decision_date >= as_of:
            counts["invalid_or_future_outcome"] += 1
            continue
        if row.public_features_as_of is None or row.public_features_as_of >= row.decision_date:
            counts["missing_predecision_features"] += 1
            continue
        if row.ascertainment_source not in DENOMINATOR_SOURCES or not row.cohort_id:
            counts["selection_biased_or_unknown_denominator"] += 1
            continue
        cohort_ids.add(row.cohort_id)
        counts[row.outcome] += 1
    eligible = counts["APPROVED"] + counts["COMPLETE_RESPONSE"]
    return {
        "status": "AUDIT_ONLY_NO_VALIDATED_PROBABILITY",
        "eligible_review_cycles": eligible,
        "outcomes": {x: counts[x] for x in sorted(OUTCOMES)},
        "excluded": {x: counts[x] for x in (
            "invalid_or_duplicate", "invalid_or_future_outcome",
            "missing_predecision_features", "selection_biased_or_unknown_denominator")},
        "cohort_ids": sorted(cohort_ids),
        "probability": None,
    }
