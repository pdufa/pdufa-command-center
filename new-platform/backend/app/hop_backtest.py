"""Leakage-controlled, walk-forward evaluation of historical FDA review cycles.

Evaluation only: the score callback is a candidate model supplied by callers.
No trained model, approval probabilities or deployment are created here.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections.abc import Mapping
import re
from datetime import date
from math import isfinite
from typing import Callable, Sequence
from .hop_outcome_cohort import OutcomeObservation, observation_exclusion
from .hop_forecast_metrics import summarize_binary_forecasts


@dataclass(frozen=True)
class PredictionCase:
    """Only predecision fields cross the scoring boundary.

    FDA decision/publication dates and postdecision cohort metadata are absent.
    The constant outcome preserves the previous masked-label callback contract.
    """
    application_id: str
    review_cycle: int
    public_features_as_of: date
    outcome: str = field(default="WITHHELD", init=False)


def _latest_application_cycles(rows):
    latest = {}
    for row in sorted(rows, key=lambda r: (r.decision_date, r.review_cycle)):
        latest[row.application_id] = row
    return list(latest.values())


def _prespecified_program_holdout(rows, program_group_by_application, heldout_program_groups):
    """Freeze complete asserted program families before accessing any outcomes."""
    if program_group_by_application is None and heldout_program_groups is None:
        return None, None
    if not isinstance(program_group_by_application, Mapping):
        raise ValueError("Complete application-to-program mapping required")
    if type(heldout_program_groups) not in (set, frozenset):
        raise ValueError("Heldout program families must be an explicit set")
    apps = {row.application_id for row in rows}
    if set(program_group_by_application) != apps:
        raise ValueError("Every application requires exactly one family; no missing or extra aliases")
    groups = {}
    for app in apps:
        group = program_group_by_application[app]
        if not isinstance(group, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.:-]{0,79}", group):
            raise ValueError("canonical, nonempty program group IDs required")
        groups[app] = group
    selected = frozenset(heldout_program_groups)
    if not selected or not selected < set(groups.values()):
        raise ValueError("Heldout families must be a nonempty proper subset of observed groups")
    return groups, selected


@dataclass(frozen=True)
class BacktestFold:
    cutoff: date
    train_count: int
    test_count: int
    eligible_test_count: int
    abstained_test_count: int
    excluded_test_count: int
    brier_score: float | None
    research_metrics: dict | None = None
    independent_fda_validation_complete: bool = False
    family_holdout_audit: dict | None = None

def walk_forward_backtest(
    rows: Sequence[OutcomeObservation],
    cutoffs: Sequence[date],
    score_fn: Callable[[Sequence[OutcomeObservation], PredictionCase], float | None],
    min_train: int = 100,
    *, evaluation_as_of: date | None = None,
    program_group_by_application: Mapping[str, str] | None = None,
    heldout_program_groups: frozenset[str] | set[str] | None = None,
) -> list[BacktestFold]:
    """Evaluate only on later decisions; no same-application outcome leakage.

    The score function must be fitted exclusively on the supplied train rows.
    Labels must have been publicly available strictly before each prediction's
    feature cutoff. Decision/publication dates and test labels are not passed to
    score_fn. The callback must not retrieve labels through other sources;
    independent model/data audit and an untouched final cohort remain required.

    A prespecified family mapping+holdout excludes all held-out families from
    every training fold. One held-out family contributes at most one test
    decision across all folds. Caller-reported group identities are NOT
    independently adjudicated and cannot confer FDA model validation.
    """
    if type(min_train) is not int or min_train < 1:
        raise ValueError("min_train must be positive")
    if any(type(c) is not date for c in cutoffs):
        raise ValueError("cutoffs must be dates")
    if list(cutoffs) != sorted(set(cutoffs)):
        raise ValueError("cutoffs must be unique and chronological")
    if len(cutoffs) < 2:
        raise ValueError("at least two cutoffs required")
    audit_as_of = cutoffs[-1] if evaluation_as_of is None else evaluation_as_of
    if type(audit_as_of) is not date or audit_as_of < cutoffs[-1]:
        raise ValueError("evaluation_as_of must be a date on or after the final cutoff")
    if any(not isinstance(r, OutcomeObservation) for r in rows):
        raise ValueError("backtest input must contain outcome observations")
    if any(not isinstance(r.application_id, str) or not r.application_id.strip()
           or type(r.review_cycle) is not int or r.review_cycle < 1 for r in rows):
        raise ValueError("exact application identity and positive integer review cycle required")
    if any(type(r.decision_date) is not date for r in rows):
        raise ValueError("FDA decision dates must be valid date objects")
    # Reject duplicate application/review-cycle labels before any evaluation.
    keys = [(r.application_id, r.review_cycle) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate application review cycle in backtest input")
    family_map, frozen_holdouts = _prespecified_program_holdout(
        rows, program_group_by_application, heldout_program_groups)
    result = []
    heldout_application_ids = set()
    heldout_group_ids = set()
    valid = [r for r in rows if observation_exclusion(r, as_of=audit_as_of) is None]
    for left, right in zip(cutoffs, cutoffs[1:]):
        train_pool = [r for r in valid if r.decision_date < left and r.outcome_public_as_of < left
                      and (family_map is None or family_map[r.application_id] not in frozen_holdouts)]
        test = [r for r in rows if type(r.decision_date) is date and left <= r.decision_date < right]
        # Multiple completed review cycles for one application must not
        # overweight that application in training. Keep its latest cycle.
        train = _latest_application_cycles(train_pool)
        train_ids = {r.application_id for r in train}
        usable = [r for r in valid if left <= r.decision_date < right
                  and r.application_id not in train_ids
                  and r.application_id not in heldout_application_ids
                  and (family_map is None or (
                      family_map[r.application_id] in frozen_holdouts
                      and family_map[r.application_id] not in heldout_group_ids))]
        # A single application must not contribute multiple held-out labels
        # within a fold, even when review-cycle identifiers differ.
        heldout_ids = set()
        fold_group_ids = set()
        unique_usable = []
        for row in sorted(usable, key=lambda r: (r.decision_date, r.review_cycle)):
            group = family_map[row.application_id] if family_map is not None else None
            if row.application_id not in heldout_ids and (group is None or group not in fold_group_ids):
                unique_usable.append(row)
                heldout_ids.add(row.application_id)
                if group is not None:
                    fold_group_ids.add(group)
        usable = unique_usable
        # Prespecify the earliest eligible cycle per held-out application across
        # all folds, including abstentions. Never select a later cycle merely
        # because its forecast would be easier or its label is published sooner.
        heldout_application_ids.update(heldout_ids)
        heldout_group_ids.update(fold_group_ids)
        losses = []
        scored_labels = []
        baseline_probabilities = []
        if len(train) >= min_train:
            for row in usable:
                # The test snapshot may predate the fold boundary. Only labels
                # decided before that snapshot can train its prediction.
                asof_train = tuple(_latest_application_cycles(
                    candidate for candidate in train_pool
                    if candidate.decision_date < row.public_features_as_of
                    and candidate.public_features_as_of < row.public_features_as_of
                    and candidate.outcome_public_as_of < row.public_features_as_of
                ))
                if len(asof_train) < min_train:
                    continue
                value = score_fn(asof_train, PredictionCase(
                    row.application_id, row.review_cycle, row.public_features_as_of))
                if value is not None:
                    if (isinstance(value, bool) or not isinstance(value, (int, float))
                            or not isfinite(value) or not 0 <= value <= 1):
                        raise ValueError("score must be a probability in [0,1] or None")
                    target = 1.0 if row.outcome == "APPROVED" else 0.0
                    losses.append((float(value)-target)**2)
                    scored_labels.append((float(value), int(target)))
                    baseline_probabilities.append(
                        sum(x.outcome == "APPROVED" for x in asof_train) / len(asof_train)
                    )
        research_metrics = summarize_binary_forecasts(
            scored_labels, eligible_count=len(usable),
            baseline_probabilities=baseline_probabilities,
        )
        result.append(BacktestFold(
            cutoff=left, train_count=len(train), test_count=len(losses),
            eligible_test_count=len(usable),
            abstained_test_count=len(usable)-len(losses),
            excluded_test_count=len(test)-len(usable),
            brier_score=sum(losses)/len(losses) if losses else None,
            research_metrics=research_metrics,
            independent_fda_validation_complete=False,
            family_holdout_audit=({
                "prespecifiedGroupHoldoutMode": True,
                "suppliedMappingCompleteForDataset": True,
                "disjointOnSuppliedMapping": True,
                "mappingIndependentlyAdjudicated": False,
                "realFdaOutcomeCohortVerified": False,
                "selectedHoldoutProgramGroups": sorted(frozen_holdouts),
                "testProgramGroupsThisFold": sorted(fold_group_ids),
                "allSelectedProgramGroupsExcludedFromTraining": True,
                "modelCalibrationIndependentlyValidated": False,
            } if family_map is not None else None),
        ))
    return result
