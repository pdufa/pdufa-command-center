# Synthetic fixtures explicitly declare publication dates; these are not real FDA source dates.
from datetime import date
from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

CUTS = [date(2020,1,1), date(2021,1,1)]

def case(app, year, source="COMPLETE_APPLICATION_COHORT", outcome="APPROVED"):
    return OutcomeObservation(app,1,date(year,6,1),outcome,source,"complete-2019-2020",date(year,1,1),True, outcome_public_as_of=date(year,6,1))

def test_crl_only_records_never_train_or_test():
    rows=[case("a",2019,source="FDA_CRL_PUBLICATION",outcome="COMPLETE_RESPONSE"),
          case("b",2020)]
    result=walk_forward_backtest(rows,CUTS,lambda train,row: 0.5,min_train=1)[0]
    assert result.train_count == 0
    assert result.test_count == 0

def test_abstentions_separate_from_exclusions():
    rows=[case("a",2019),case("b",2020),case("c",2020,source="FDA_CRL_PUBLICATION")]
    result=walk_forward_backtest(rows,CUTS,lambda train,row: None,min_train=1)[0]
    assert result.eligible_test_count == 1
    assert result.abstained_test_count == 1
    assert result.excluded_test_count == 1
    assert result.test_count == 0
    assert result.brier_score is None
