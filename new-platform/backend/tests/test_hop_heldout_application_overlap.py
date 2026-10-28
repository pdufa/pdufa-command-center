# Synthetic fixtures explicitly declare publication dates; these are not real FDA source dates.
from datetime import date
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def make_row(app, cycle, year):
    return OutcomeObservation(app, cycle, date(year,6,1), 'APPROVED', 'COMPLETE_APPLICATION_COHORT', 'cohort', date(year,1,1), True, outcome_public_as_of=date(year,6,1))

def test_heldout_application_not_scored_twice():
    rows = [make_row('train',1,2019), make_row('test',1,2020), make_row('test',2,2020)]
    scored = []
    def score(train, case):
        scored.append(case.application_id)
        return 0.5
    fold = walk_forward_backtest(rows,[date(2020,1,1),date(2021,1,1)],score,min_train=1)[0]
    assert scored == ['test']
    assert fold.eligible_test_count == 1
    assert fold.excluded_test_count == 1
