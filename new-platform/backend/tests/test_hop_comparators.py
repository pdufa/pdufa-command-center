from datetime import date, timedelta
from app.hop_comparators import HistoricalCase, TargetCase, match_historical_cases, prediction_status

AS_OF = date(2026, 10, 25)
TARGET = TargetCase("lung cancer", "oncology", "antibody", 3, AS_OF)

def record(case_id, decision, evidence, outcome="APPROVED", url="https://www.fda.gov/example"):
    return HistoricalCase(case_id, "lung cancer", "oncology", "antibody", 3, decision, outcome, evidence, url)

def test_excludes_future_and_unverified_decisions():
    records = [
        record("old", AS_OF-timedelta(days=10), AS_OF-timedelta(days=9)),
        record("future", AS_OF+timedelta(days=1), AS_OF-timedelta(days=1)),
        record("late_evidence", AS_OF-timedelta(days=10), AS_OF+timedelta(days=1)),
        record("unverified", AS_OF-timedelta(days=10), AS_OF-timedelta(days=1), url=""),
        record("unknown", AS_OF-timedelta(days=10), AS_OF-timedelta(days=1), outcome="PENDING"),
    ]
    assert [x.case_id for x in match_historical_cases(TARGET, records)] == ["old"]

def test_similarity_is_not_probability():
    matches = match_historical_cases(TARGET, [record("old", AS_OF-timedelta(days=20), AS_OF-timedelta(days=19))])
    assert matches[0].similarity == 1.0
    assert prediction_status(matches) == {"status":"NOT_VALIDATED","probability":None,"comparator_count":1}

def test_no_evidence_means_abstain():
    assert prediction_status(match_historical_cases(TARGET, []))["probability"] is None
