# Synthetic fixtures explicitly declare publication dates; these are not real FDA source dates.
from datetime import date
import pytest
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

def test_duplicate_cycle_rejected():
    row=OutcomeObservation('sample',1,date(2019,6,1),'APPROVED','COMPLETE_APPLICATION_COHORT','cohort',date(2019,1,1),True, outcome_public_as_of=date(2019,6,1))
    with pytest.raises(ValueError,match='duplicate application review cycle'):
        walk_forward_backtest([row,row],[date(2020,1,1),date(2021,1,1)],lambda a,b:0.5,min_train=1)
