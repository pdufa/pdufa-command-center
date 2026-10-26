"""Leakage-controlled, walk-forward evaluation of historical FDA review cycles.

Evaluation only: the score callback is a candidate model supplied by callers.
No trained model, approval probabilities or deployment are created here.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from datetime import date
from math import isfinite
from typing import Callable, Sequence
from .hop_outcome_cohort import OutcomeObservation, DENOMINATOR_SOURCES, OUTCOMES

@dataclass(frozen=True)
class BacktestFold:
    cutoff: date
    train_count: int
    test_count: int
    eligible_test_count: int
    abstained_test_count: int
    excluded_test_count: int
    brier_score: float | None

def walk_forward_backtest(
    rows: Sequence[OutcomeObservation],
    cutoffs: Sequence[date],
    score_fn: Callable[[Sequence[OutcomeObservation], OutcomeObservation], float | None],
    min_train: int = 100,
) -> list[BacktestFold]:
    """Evaluate only on later decisions; no same-application outcome leakage.

    The score function must be fitted exclusively on the supplied train rows.
    Test outcomes are withheld from score_fn. The callback must not fetch\n    outcome labels through external sources; independent audit still required.
    """
    if min_train < 1:
        raise ValueError("min_train must be positive")
    if list(cutoffs) != sorted(set(cutoffs)):
        raise ValueError("cutoffs must be unique and chronological")
    if len(cutoffs) < 2:
        raise ValueError("at least two cutoffs required")
    # Reject duplicate application/review-cycle labels before any evaluation.
    keys = [(r.application_id, r.review_cycle) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate application review cycle in backtest input")
    result = []
    for left, right in zip(cutoffs, cutoffs[1:]):
        train = [r for r in rows if r.decision_date < left]
        test = [r for r in rows if left <= r.decision_date < right]
        train = [r for r in train if r.public_features_as_of is not None
                 and r.public_features_as_of < r.decision_date
                 and r.ascertainment_source in DENOMINATOR_SOURCES
                 and r.outcome in OUTCOMES and r.cohort_id
                 and r.cohort_complete_verified is True]
        # Multiple completed review cycles for one application must not
        # overweight that application in training. Keep its latest cycle.
        latest_train = {}
        for row in sorted(train, key=lambda r: (r.decision_date, r.review_cycle)):
            latest_train[row.application_id] = row
        train = list(latest_train.values())
        train_ids = set(latest_train)
        usable = [r for r in test if r.application_id not in train_ids
                  and r.public_features_as_of is not None
                  and r.public_features_as_of < r.decision_date
                  and r.ascertainment_source in DENOMINATOR_SOURCES
                  and r.outcome in OUTCOMES and r.cohort_id
                  and r.cohort_complete_verified is True]
        # A single application must not contribute multiple held-out labels
        # within a fold, even when review-cycle identifiers differ.
        heldout_ids = set()
        unique_usable = []
        for row in sorted(usable, key=lambda r: (r.decision_date, r.review_cycle)):
            if row.application_id not in heldout_ids:
                unique_usable.append(row)
                heldout_ids.add(row.application_id)
        usable = unique_usable
        losses = []
        if len(train) >= min_train:
            for row in usable:
                # The test snapshot may predate the fold boundary. Only labels
                # decided before that snapshot can train its prediction.
                asof_train = tuple(
                    candidate for candidate in train
                    if candidate.decision_date < row.public_features_as_of
                    and candidate.public_features_as_of < row.public_features_as_of
                )
                if len(asof_train) < min_train:
                    continue
                value = score_fn(asof_train, replace(row, outcome="WITHHELD"))
                if value is not None:
                    if (isinstance(value, bool) or not isinstance(value, (int, float))
                            or not isfinite(value) or not 0 <= value <= 1):
                        raise ValueError("score must be a probability in [0,1] or None")
                    target = 1.0 if row.outcome == "APPROVED" else 0.0
                    losses.append((float(value)-target)**2)
        result.append(BacktestFold(
            cutoff=left, train_count=len(train), test_count=len(losses),
            eligible_test_count=len(usable),
            abstained_test_count=len(usable)-len(losses),
            excluded_test_count=len(test)-len(usable),
            brier_score=sum(losses)/len(losses) if losses else None,
        ))
    return result
