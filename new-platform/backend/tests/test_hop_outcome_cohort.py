from datetime import date
from app.hop_outcome_cohort import OutcomeObservation, audit_outcome_cohort

def row(app, outcome, source="COMPLETE_APPLICATION_COHORT", feature_date=date(2020,1,1), cycle=1):
    return OutcomeObservation(app, cycle, date(2020,6,1), outcome, source, "cohort-2020", feature_date, True)

def test_crl_publication_is_not_representative_denominator():
    result = audit_outcome_cohort([row("A", "COMPLETE_RESPONSE", "FDA_CRL_PUBLICATION")], date(2021,1,1))
    assert result["eligible_review_cycles"] == 0
    assert result["excluded"]["selection_biased_or_unknown_denominator"] == 1
    assert result["probability"] is None

def test_approval_and_crl_review_cycles_count_separately():
    result = audit_outcome_cohort([row("A", "COMPLETE_RESPONSE"), row("A", "APPROVED", cycle=2)], date(2021,1,1))
    assert result["eligible_review_cycles"] == 2
    assert result["outcomes"] == {"APPROVED":1, "COMPLETE_RESPONSE":1}
    assert result["probability"] is None

def test_no_future_or_postdecision_features():
    result = audit_outcome_cohort([row("A","APPROVED",feature_date=date(2020,6,2)),row("B","APPROVED")],date(2020,5,1))
    assert result["eligible_review_cycles"] == 0
    assert sum(result["excluded"].values()) == 2

def test_duplicate_cycle_excluded():
    result = audit_outcome_cohort([row("A","APPROVED"),row("A","APPROVED")],date(2021,1,1))
    assert result["eligible_review_cycles"] == 1
    assert result["excluded"]["invalid_or_duplicate"] == 1
