from datetime import date
import pytest
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def row(app, year, outcome="APPROVED", evidence_year=None):
    return OutcomeObservation(app, 1, date(year, 6, 1), outcome,
                              "COMPLETE_APPLICATION_COHORT", "cohort", date(evidence_year or year, 1, 1), True)

def test_empty_history_abstains():
    folds = walk_forward_backtest([], [date(2020,1,1), date(2021,1,1)], lambda train, case: 0.5)
    assert folds[0].brier_score is None
    assert folds[0].test_count == 0

def test_walk_forward_only_earlier_training():
    records = [row("old",2019),row("new",2020,"COMPLETE_RESPONSE")]
    seen = []
    def score(train, test):
        seen.append(([x.application_id for x in train], test.application_id))
        return 0.25
    folds = walk_forward_backtest(records,[date(2020,1,1),date(2021,1,1)],score,min_train=1)
    assert seen == [(["old"],"new")]
    assert folds[0].brier_score == pytest.approx(0.0625)

def test_repeated_application_is_excluded():
    records = [row("same",2019),row("same",2020)]
    folds = walk_forward_backtest(records,[date(2020,1,1),date(2021,1,1)],lambda train, case: 0.9,min_train=1)
    assert folds[0].excluded_test_count == 1
    assert folds[0].brier_score is None

def test_invalid_score_rejected():
    records = [row("old",2019),row("new",2020)]
    with pytest.raises(ValueError):
        walk_forward_backtest(records,[date(2020,1,1),date(2021,1,1)],lambda train, case: 1.5,min_train=1)
