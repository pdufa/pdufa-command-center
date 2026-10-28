"""Synthetic leakage regressions, never observed FDA prediction accuracy."""
from dataclasses import replace
from datetime import date, datetime

import pytest

from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation, audit_outcome_cohort, OUTCOME_TAXONOMY

CUTS = [date(2020, 1, 1), date(2021, 1, 1)]


def row(app, year, *, publication=None, feature=None, cycle=1, outcome="APPROVED"):
    return OutcomeObservation(app, cycle, date(year, 6, 1), outcome,
                              "COMPLETE_APPLICATION_COHORT", "synthetic-cohort",
                              feature or date(year, 1, 1), True,
                              outcome_public_as_of=publication)


def known():
    return row("known", 2017, publication=date(2017, 6, 1))


def heldout(**changes):
    return row("heldout", 2020, publication=date(2020, 6, 1), **changes)


def test_unknown_label_publication_never_defaults_to_the_decision_date():
    missing = row("unknown", 2019)
    audit = audit_outcome_cohort([missing], date(2021, 1, 1))
    assert audit["eligible_review_cycles"] == 0
    assert audit["excluded"]["unknown_outcome_publication"] == 1
    fold = walk_forward_backtest([missing, heldout()], CUTS,
        lambda train, case: pytest.fail("Unknown-publication label must not train"), min_train=1)[0]
    assert fold.train_count == 0 and fold.test_count == 0
    assert fold.abstained_test_count == 1 and fold.brier_score is None


def test_effective_action_date_does_not_make_a_later_published_label_available():
    late = row("late-publication", 2018, publication=date(2020, 2, 1))
    seen = []
    fold = walk_forward_backtest([known(), late, heldout()], CUTS,
        lambda train, case: seen.append([r.application_id for r in train]) or .5, min_train=1)[0]
    assert seen == [["known"]]
    assert fold.train_count == fold.test_count == 1


def test_same_day_publication_cannot_enter_an_earlier_time_of_day_prediction():
    same_day = row("same-day", 2018, publication=date(2019, 1, 1))
    seen = []
    walk_forward_backtest([known(), same_day, heldout(feature=date(2019, 1, 1))], CUTS,
        lambda train, case: seen.append([r.application_id for r in train]) or .5, min_train=1)
    assert seen == [["known"]]


def test_late_ground_truth_requires_an_explicit_later_evaluation_snapshot():
    late_truth = replace(heldout(), outcome_public_as_of=date(2022, 1, 1))
    fold = walk_forward_backtest([known(), late_truth], CUTS,
        lambda train, case: pytest.fail("Truth not yet public at evaluation cutoff"), min_train=1)[0]
    assert fold.eligible_test_count == 0 and fold.excluded_test_count == 1
    assert fold.test_count == 0 and fold.brier_score is None
    observed = []
    later = walk_forward_backtest([known(), late_truth], CUTS,
        lambda train, case: observed.append(case.application_id) or .5,
        min_train=1, evaluation_as_of=date(2023, 1, 1))[0]
    assert observed == ["heldout"] and later.test_count == 1


def test_impossible_publication_before_fda_action_is_excluded():
    invalid = replace(heldout(), outcome_public_as_of=date(2019, 1, 1))
    audit = audit_outcome_cohort([invalid], date(2021, 1, 1))
    assert audit["eligible_review_cycles"] == 0
    assert audit["excluded"]["outcome_publication_before_action"] == 1


def test_conflicting_action_claims_quarantine_the_entire_cycle_in_either_order():
    approved = heldout()
    denied = replace(approved, outcome="COMPLETE_RESPONSE")
    forward = audit_outcome_cohort([approved, denied], date(2021,1,1))
    reverse = audit_outcome_cohort([denied, approved], date(2021,1,1))
    assert forward == reverse
    assert forward["eligible_review_cycles"] == 0
    assert forward["excluded"]["conflicting_application_review_cycle"] == 2


def test_taxonomy_has_exactly_two_binary_actions():
    labels = {k:v["binary_label"] for k,v in OUTCOME_TAXONOMY.items() if v["binary_label"] is not None}
    assert labels == {"APPROVED":1,"COMPLETE_RESPONSE":0}
    assert all(OUTCOME_TAXONOMY[k]["binary_label"] is None for k in
               ("POSTPONED","REVISED_PDUFA","WITHDRAWN","REFUSE_TO_FILE","OTHER_NONAPPROVAL","UNRESOLVED"))


def test_scorer_cannot_see_future_decision_publication_or_cohort_metadata():
    observed = []
    def score(train, case):
        assert case.outcome == "WITHHELD"
        assert case.public_features_as_of == date(2020, 1, 1)
        assert not hasattr(case, "decision_date")
        assert not hasattr(case, "outcome_public_as_of")
        assert not hasattr(case, "cohort_complete_verified")
        assert not hasattr(case, "ascertainment_source")
        observed.append(case.application_id)
        return .5
    fold = walk_forward_backtest([known(), heldout(outcome="COMPLETE_RESPONSE")], CUTS, score, min_train=1)[0]
    assert observed == ["heldout"] and fold.test_count == 1


def test_latest_cycle_selection_happens_after_the_prediction_cutoff_filter():
    earlier = row("repeated", 2017, cycle=1, publication=date(2017, 6, 1))
    later = row("repeated", 2019, cycle=2, publication=date(2019, 6, 1))
    observed = []
    fold = walk_forward_backtest([earlier, later, heldout(feature=date(2018, 1, 1))], CUTS,
        lambda train, case: observed.extend((r.application_id, r.review_cycle) for r in train) or .5,
        min_train=1)[0]
    assert observed == [("repeated", 1)] and fold.test_count == 1


@pytest.mark.parametrize("score", [.5, None])
def test_delayed_publication_does_not_repeat_the_same_heldout_application_across_folds(score):
    first = row("heldout-repeat", 2020, cycle=1, publication=date(2024,1,1))
    second = row("heldout-repeat", 2021, cycle=2, publication=date(2024,1,1))
    seen = []
    folds = walk_forward_backtest([known(), first, second],
        [date(2020,1,1),date(2021,1,1),date(2022,1,1)],
        lambda train, case: seen.append((case.application_id,case.review_cycle)) or score,
        min_train=1, evaluation_as_of=date(2025,1,1))
    assert seen == [("heldout-repeat",1)]
    assert sum(f.eligible_test_count for f in folds) == 1
    assert folds[1].excluded_test_count == 1
    assert sum(f.abstained_test_count for f in folds) == (1 if score is None else 0)


@pytest.mark.parametrize("action", ["WITHDRAWN", "POSTPONED", "REVISED_PDUFA", "REFUSE_TO_FILE", "OTHER_NONAPPROVAL", "UNRESOLVED"])
def test_nonbinary_events_are_not_silently_scored_as_failures(action):
    fold = walk_forward_backtest([known(), heldout(outcome=action)], CUTS,
        lambda train, case: pytest.fail("Nonbinary action must stay excluded"), min_train=1)[0]
    assert fold.eligible_test_count == fold.test_count == 0
    assert fold.excluded_test_count == 1 and fold.brier_score is None


@pytest.mark.parametrize("value", [True, False, 1.5, 0, -1])
def test_minimum_training_support_is_a_positive_integer(value):
    with pytest.raises(ValueError, match="positive"):
        walk_forward_backtest([], CUTS, lambda a,b: .5, min_train=value)


@pytest.mark.parametrize("value", ["2021-01-01", datetime(2021,1,1), date(2020,12,31)])
def test_evaluation_date_is_explicit_and_covers_the_final_fold(value):
    with pytest.raises(ValueError, match="evaluation_as_of"):
        walk_forward_backtest([], CUTS, lambda a,b: .5, evaluation_as_of=value)


@pytest.mark.parametrize("value", [None,"2020-06-01",datetime(2020,6,1)])
def test_invalid_decision_dates_cannot_silently_disappear_from_fold_accounting(value):
    with pytest.raises(ValueError, match="decision dates"):
        walk_forward_backtest([replace(heldout(), decision_date=value)], CUTS, lambda a,b: .5)
