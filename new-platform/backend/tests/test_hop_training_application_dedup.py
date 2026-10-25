from datetime import date
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def row(app,cycle,year):
    return OutcomeObservation(app,cycle,date(year,6,1),'APPROVED','COMPLETE_APPLICATION_COHORT','cohort',date(year,1,1),True)

def test_training_application_not_weighted_twice():
    rows=[row('repeat',1,2018),row('repeat',2,2019),row('heldout',1,2020)]
    observed=[]
    def score(train,case):
        observed.extend((r.application_id,r.review_cycle) for r in train)
        return 0.5
    fold=walk_forward_backtest(rows,[date(2020,1,1),date(2021,1,1)],score,min_train=1)[0]
    assert observed == [('repeat',2)]
    assert fold.train_count == 1
    assert fold.test_count == 1
