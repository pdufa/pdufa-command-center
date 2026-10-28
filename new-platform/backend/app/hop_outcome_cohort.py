"""HOP outcome cohort quality checks; prevents biased CRL archive as denominator.

A historical decision must be sampled from a defined, complete application
cohort before its outcome is used to estimate an approval rate. CRL publication
alone does not establish a representative sample.
"""
from __future__ import annotations
from collections import Counter, defaultdict
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
    cohort_complete_verified: bool = False
    # Public availability of the action label, not its printed/effective date.
    # Unknown stays unknown: never default this clock to the decision date.
    outcome_public_as_of: date | None = None

# These are action categories, not string aliases for one negative class.
# Unknown/pre-review/censoring events never become binary nonapproval labels.
OUTCOME_TAXONOMY = {
    "APPROVED": {"binary_label": 1, "meaning": "Approval at the specified review-cycle action"},
    "COMPLETE_RESPONSE": {"binary_label": 0, "meaning": "Documented nonapproval action at that cycle"},
    "POSTPONED": {"binary_label": None, "meaning": "No binary decision observed at the original target"},
    "REVISED_PDUFA": {"binary_label": None, "meaning": "Target-date revision; preserve dated event history"},
    "WITHDRAWN": {"binary_label": None, "meaning": "Withdrawal is not automatically an FDA rejection"},
    "REFUSE_TO_FILE": {"binary_label": None, "meaning": "Pre-review filing action, outside this binary target"},
    "OTHER_NONAPPROVAL": {"binary_label": None, "meaning": "Unresolved legacy category; exact action required"},
    "UNRESOLVED": {"binary_label": None, "meaning": "Missing or unresolved action evidence"},
}
OUTCOMES = {key for key, item in OUTCOME_TAXONOMY.items() if item["binary_label"] is not None}
DENOMINATOR_SOURCES = {"COMPLETE_APPLICATION_COHORT"}


def observation_exclusion(row: OutcomeObservation, *, as_of: date) -> str | None:
    """Metadata gate only; source truth and denominator proof remain upstream."""
    if (not isinstance(row, OutcomeObservation) or not isinstance(row.application_id, str)
            or not row.application_id.strip() or type(row.review_cycle) is not int
            or row.review_cycle < 1 or type(row.decision_date) is not date):
        return "invalid_or_duplicate"
    if not isinstance(row.outcome, str) or row.outcome not in OUTCOMES or row.decision_date >= as_of:
        return "invalid_or_future_outcome"
    if type(row.public_features_as_of) is not date or row.public_features_as_of >= row.decision_date:
        return "missing_predecision_features"
    if (not isinstance(row.ascertainment_source, str)
            or row.ascertainment_source not in DENOMINATOR_SOURCES
            or not isinstance(row.cohort_id, str) or not row.cohort_id.strip()
            or row.cohort_complete_verified is not True):
        return "selection_biased_or_unknown_denominator"
    if type(row.outcome_public_as_of) is not date:
        return "unknown_outcome_publication"
    if row.outcome_public_as_of < row.decision_date:
        return "outcome_publication_before_action"
    if row.outcome_public_as_of > as_of:
        return "outcome_not_yet_public"
    return None

def audit_outcome_cohort(rows: Iterable[OutcomeObservation], as_of: date) -> dict:
    """Return auditable counts, not an approval probability."""
    if type(as_of) is not date:
        raise ValueError("as_of must be a date")
    counts = Counter()
    rows = list(rows)
    # Reconcile all action claims before counting any cycle. Otherwise the first
    # row silently wins when a later source contradicts its label/action date.
    claims = defaultdict(set)
    for row in rows:
        if (isinstance(row, OutcomeObservation) and isinstance(row.application_id, str)
                and type(row.review_cycle) is int and isinstance(row.outcome, str)
                and type(row.decision_date) is date):
            claims[(row.application_id, row.review_cycle)].add((row.outcome, row.decision_date))
    conflicts = {key for key, values in claims.items() if len(values) > 1}
    seen = set()
    cohort_ids = set()
    for row in rows:
        reason = observation_exclusion(row, as_of=as_of)
        if reason is not None:
            counts[reason] += 1
            continue
        key = (row.application_id, row.review_cycle)
        if key in conflicts:
            counts["conflicting_application_review_cycle"] += 1
            continue
        if not row.application_id or row.review_cycle < 1 or key in seen:
            counts["invalid_or_duplicate"] += 1
            continue
        seen.add(key)
        cohort_ids.add(row.cohort_id)
        counts[row.outcome] += 1
    eligible = counts["APPROVED"] + counts["COMPLETE_RESPONSE"]
    return {
        "status": "AUDIT_ONLY_NO_VALIDATED_PROBABILITY",
        "eligible_review_cycles": eligible,
        "outcomes": {x: counts[x] for x in sorted(OUTCOMES)},
        "excluded": {x: counts[x] for x in (
            "invalid_or_duplicate", "invalid_or_future_outcome",
            "missing_predecision_features", "selection_biased_or_unknown_denominator",
            "unknown_outcome_publication", "outcome_publication_before_action",
            "outcome_not_yet_public", "conflicting_application_review_cycle")},
        "cohort_ids": sorted(cohort_ids),
        "probability": None,
    }
