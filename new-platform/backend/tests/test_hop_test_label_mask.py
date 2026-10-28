# Synthetic fixtures explicitly declare publication dates; these are not real FDA source dates.
from datetime import date
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def test_scoring_callback_cannot_see_heldout_outcome():
    rows=[
        OutcomeObservation("A",1,date(2019,6,1),"APPROVED","COMPLETE_APPLICATION_COHORT","c",date(2019,1,1),True, outcome_public_as_of=date(2019,6,1)),
        OutcomeObservation("B",1,date(2020,6,1),"COMPLETE_RESPONSE","COMPLETE_APPLICATION_COHORT","c",date(2020,1,1),True, outcome_public_as_of=date(2020,6,1)),
    ]
    seen=[]
    def scorer(train, case):
        seen.append((train[0].outcome, case.outcome))
        return 0.1
    result=walk_forward_backtest(rows,[date(2020,1,1),date(2021,1,1)],scorer,min_train=1)
    assert seen == [("APPROVED","WITHHELD")]
    assert result[0].test_count == 1
