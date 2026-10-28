"""Synthetic allocation regressions, never real FDA prediction validation."""
from dataclasses import replace
from datetime import date

import pytest

from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation


def observation(app, year, *, cycle=1, outcome="APPROVED", publication="same"):
    action = date(year, 6, 1)
    return OutcomeObservation(
        app, cycle, action, outcome, "COMPLETE_APPLICATION_COHORT", "SYNTHETIC",
        date(year, 1, 1), True,
        outcome_public_as_of=action if publication == "same" else publication,
    )


@pytest.mark.parametrize("publication", [None, date(2022, 1, 1), date(2020, 5, 31)])
def test_unavailable_or_invalid_first_label_does_not_select_a_later_published_approval(publication):
    rows = [
        observation("TRAIN", 2019),
        observation("HOLD", 2020, outcome="COMPLETE_RESPONSE", publication=publication),
        replace(observation("HOLD", 2020, cycle=2), decision_date=date(2020, 9, 1), outcome_public_as_of=date(2020, 9, 1)),
    ]
    for ordered in (rows, list(reversed(rows))):
        folds = walk_forward_backtest(
            ordered, [date(2020, 1, 1), date(2021, 1, 1)],
            lambda *_: pytest.fail("a published later approval must not replace the selected first cycle"),
            min_train=1,
        )
        assert folds[0].eligible_test_count == folds[0].test_count == 0
        assert folds[0].excluded_test_count == 2
        assert folds[0].research_metrics["coverage"] is None
        assert folds[0].research_metrics["accuracy"] is None
        assert folds[0].independent_fda_validation_complete is False


def test_unavailable_first_cycle_reserves_application_across_folds():
    rows = [observation("TRAIN", 2019),
            observation("HOLD", 2020, outcome="COMPLETE_RESPONSE", publication=None),
            observation("HOLD", 2021, cycle=2)]
    folds = walk_forward_backtest(
        rows, [date(2020, 1, 1), date(2021, 1, 1), date(2022, 1, 1)],
        lambda *_: pytest.fail("later folds must preserve the originally allocated cycle"), min_train=1,
    )
    assert [fold.eligible_test_count for fold in folds] == [0, 0]
    assert [fold.excluded_test_count for fold in folds] == [1, 1]


def test_program_holdout_does_not_replace_unavailable_crl_with_later_sibling_approval():
    rows = [observation("TRAIN", 2019),
            observation("A1", 2020, outcome="COMPLETE_RESPONSE", publication=None),
            observation("A2", 2021)]
    folds = walk_forward_backtest(
        rows, [date(2020, 1, 1), date(2021, 1, 1), date(2022, 1, 1)],
        lambda *_: pytest.fail("same-family published approval cannot replace an unavailable CRL"),
        min_train=1, program_group_by_application={"TRAIN":"CONTROL", "A1":"HOLDOUT", "A2":"HOLDOUT"},
        heldout_program_groups={"HOLDOUT"},
    )
    assert [fold.eligible_test_count for fold in folds] == [0, 0]
    assert folds[0].family_holdout_audit["reservedUnscorableProgramGroupsThisFold"] == ["HOLDOUT"]
    assert folds[1].family_holdout_audit["testProgramGroupsThisFold"] == []


def test_later_audit_scores_original_first_cycle_instead_of_reselecting_published_cycle():
    rows = [
        observation("TRAIN", 2019),
        observation("HOLD", 2020, outcome="COMPLETE_RESPONSE", publication=date(2022, 1, 1)),
        replace(observation("HOLD", 2020, cycle=2), decision_date=date(2020, 9, 1), outcome_public_as_of=date(2020, 9, 1)),
    ]
    selected = []
    folds = walk_forward_backtest(
        rows, [date(2020, 1, 1), date(2021, 1, 1)],
        lambda train, case: selected.append((case.application_id, case.review_cycle)) or None,
        min_train=1, evaluation_as_of=date(2023, 1, 1),
    )
    assert selected == [("HOLD", 1)]
    assert folds[0].eligible_test_count == folds[0].abstained_test_count == 1
    assert folds[0].excluded_test_count == 1
    assert folds[0].brier_score is None


def test_same_day_family_ties_are_deterministic_before_publication_filtering():
    rows = [observation("TRAIN", 2019),
            observation("A1", 2020, outcome="COMPLETE_RESPONSE", publication=None),
            observation("A2", 2020)]
    for ordered in (rows, list(reversed(rows))):
        fold = walk_forward_backtest(
            ordered, [date(2020, 1, 1), date(2021, 1, 1)],
            lambda *_: pytest.fail("row order must not select the published same-day sibling"),
            min_train=1, program_group_by_application={"TRAIN":"CONTROL", "A1":"HOLDOUT", "A2":"HOLDOUT"},
            heldout_program_groups={"HOLDOUT"},
        )[0]
        assert fold.eligible_test_count == 0
        assert fold.excluded_test_count == 2
