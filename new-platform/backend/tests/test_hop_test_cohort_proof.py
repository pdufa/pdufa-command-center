# Synthetic fixtures explicitly declare publication dates; these are not real FDA source dates.
from datetime import date
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def test_unverified_heldout_cohort_is_not_scored():
    rows=[
        OutcomeObservation("train",1,date(2019,6,1),"APPROVED",
            "COMPLETE_APPLICATION_COHORT","c",date(2019,1,1),True, outcome_public_as_of=date(2019,6,1)),
        OutcomeObservation("unverified",1,date(2020,6,1),"COMPLETE_RESPONSE",
            "COMPLETE_APPLICATION_COHORT","c",date(2020,1,1),False, outcome_public_as_of=date(2020,6,1)),
    ]
    invoked=[]
    def scorer(train,row):
        invoked.append(row.application_id)
        return 0.5
    fold=walk_forward_backtest(rows,[date(2020,1,1),date(2021,1,1)],scorer,min_train=1)[0]
    assert fold.train_count == 1
    assert fold.eligible_test_count == 0
    assert fold.excluded_test_count == 1
    assert fold.test_count == 0
    assert fold.brier_score is None
    assert invoked == []
