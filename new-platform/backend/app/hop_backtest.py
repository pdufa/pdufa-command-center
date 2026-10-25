"""Leakage-controlled, walk-forward evaluation of historical FDA review cycles.

Evaluation only: the score callback is a candidate model supplied by callers.
No trained model, approval probabilities or deployment are created here.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Callable, Sequence
from .hop_outcome_cohort import OutcomeObservation, audit_outcome_cohort

@dataclass(frozen=True)
class BacktestFold:
    cutoff: date
    train_count: int
    test_count: int
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
    This interface cannot itself verify its internals; external audit required.
    """
    if min_train < 1:
        raise ValueError("min_train must be positive")
    if list(cutoffs) != sorted(set(cutoffs)):
        raise ValueError("cutoffs must be unique and chronological")
    if len(cutoffs) < 2:
        raise ValueError("at least two cutoffs required")
    result = []
    for left, right in zip(cutoffs, cutoffs[1:]):
        train = [r for r in rows if r.decision_date < left]
        test = [r for r in rows if left <= r.decision_date < right]
        train = [r for r in train if r.public_features_as_of is not None
                 and r.public_features_as_of < r.decision_date]
        train_ids = {r.application_id for r in train}
        usable = [r for r in test if r.application_id not in train_ids
                  and r.public_features_as_of is not None
                  and r.public_features_as_of < r.decision_date]
        losses = []
        if len(train) >= min_train:
            for row in usable:
                value = score_fn(tuple(train), row)
                if value is not None:
                    if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                        raise ValueError("score must be a probability in [0,1] or None")
                    target = 1.0 if row.outcome == "APPROVED" else 0.0
                    losses.append((float(value)-target)**2)
        result.append(BacktestFold(
            cutoff=left, train_count=len(train), test_count=len(losses),
            excluded_test_count=len(test)-len(usable),
            brier_score=sum(losses)/len(losses) if losses else None,
        ))
    return result
