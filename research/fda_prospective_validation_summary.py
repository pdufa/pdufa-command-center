"""Research-only prospective validation coverage report.

Counts are descriptive and never interpreted as calibrated probability
or validated predictive accuracy without independent provenance.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from research.fda_prospective_outcome_scoring import Score


@dataclass(frozen=True)
class ValidationSummary:
    total: int
    scored_unverified: int
    abstentions: int
    provenance_blocked: int
    other_unscored: int
    validated_accuracy: None = None


def summarize_research_scores(scores: Iterable[Score]) -> ValidationSummary:
    rows = list(scores)
    counts = Counter(row.status for row in rows)
    return ValidationSummary(
        total=len(rows),
        scored_unverified=counts["SCORED"],
        abstentions=counts["ABSTAIN"],
        provenance_blocked=counts["PROVENANCE_NOT_VERIFIED"],
        other_unscored=sum(
            count for status, count in counts.items()
            if status not in {"SCORED", "ABSTAIN", "PROVENANCE_NOT_VERIFIED"}
        ),
    )
