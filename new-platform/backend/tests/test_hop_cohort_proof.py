from datetime import date
from app.hop_outcome_cohort import OutcomeObservation, audit_outcome_cohort
from app.hop_backtest import walk_forward_backtest

def observation(app, year, verified=False):
    return OutcomeObservation(app,1,date(year,6,1),"APPROVED",
        "COMPLETE_APPLICATION_COHORT","claimed-cohort",date(year,1,1),verified)

def test_cohort_name_alone_is_not_proof():
    result=audit_outcome_cohort([observation("a",2019)],date(2021,1,1))
    assert result["eligible_review_cycles"] == 0
    assert result["excluded"]["selection_biased_or_unknown_denominator"] == 1

def test_unverified_cohort_cannot_train_or_score():
    rows=[observation("a",2019),observation("b",2020,True)]
    result=walk_forward_backtest(rows,[date(2020,1,1),date(2021,1,1)],
        lambda train,row:0.5,min_train=1)[0]
    assert result.train_count == 0
    assert result.test_count == 0
