"""Research-only comparator tests; cases are synthetic, not FDA decisions."""
from dataclasses import replace
from datetime import date, timedelta
from itertools import count
import pytest

from app.hop_comparators import HistoricalCase, TargetCase, match_historical_cases, prediction_status

AS_OF = date(2026, 10, 25)
TARGET = TargetCase("lung cancer", "oncology", "antibody", 3, AS_OF)
APPLICATIONS = count(1)


def record(case_id, decision, evidence, outcome="APPROVED", url="https://www.fda.gov/example", *,
           features=None, adjudicated=True):
    return HistoricalCase(
        case_id, "lung cancer", "oncology", "antibody", 3, decision, outcome, evidence, url,
        public_features_as_of=features if features is not None else decision - timedelta(days=30),
        independently_adjudicated=adjudicated,
        application_id=f"NDA{next(APPLICATIONS):06d}", review_cycle=1,
    )


def test_excludes_future_and_unverified_decisions():
    records = [
        record("old", AS_OF - timedelta(days=10), AS_OF - timedelta(days=9)),
        record("future", AS_OF + timedelta(days=1), AS_OF + timedelta(days=2)),
        record("late_evidence", AS_OF - timedelta(days=10), AS_OF + timedelta(days=1)),
        record("unverified_source", AS_OF - timedelta(days=10), AS_OF - timedelta(days=9), url=""),
        record("unknown", AS_OF - timedelta(days=10), AS_OF - timedelta(days=9), outcome="PENDING"),
        record("not_adjudicated", AS_OF - timedelta(days=10), AS_OF - timedelta(days=9), adjudicated=False),
    ]
    assert [x.case_id for x in match_historical_cases(TARGET, records)] == ["old"]


def test_similarity_is_not_probability():
    decision = AS_OF - timedelta(days=20)
    matches = match_historical_cases(TARGET, [record("old", decision, decision)])
    assert matches[0].similarity == 1.0
    assert prediction_status(matches) == {"status": "NOT_VALIDATED", "probability": None, "comparator_count": 1}


def test_no_evidence_means_abstain():
    assert prediction_status(match_historical_cases(TARGET, []))["probability"] is None


def test_comparator_rejects_non_fda_domain_and_predecision_outcome_evidence():
    decision = AS_OF - timedelta(days=20)
    records = [
        record("external", decision, decision, url="https://example.org/approval"),
        record("spoofed", decision, decision, url="https://www.fda.gov.evil.test/approval"),
        record("before_decision", decision, decision - timedelta(days=1)),
        record("decision_day", decision, decision),
        record("after_decision", decision, decision + timedelta(days=1)),
    ]
    assert [x.case_id for x in match_historical_cases(TARGET, records)] == ["after_decision", "decision_day"]


def test_historical_features_must_precede_decision_and_be_dated():
    decision = AS_OF - timedelta(days=20)
    valid = record("valid", decision, decision)
    records = [
        replace(valid, case_id="undated", application_id="BLA000001", public_features_as_of=None),
        replace(valid, case_id="postdecision", application_id="BLA000002", public_features_as_of=decision + timedelta(days=1)),
        replace(valid, case_id="decision_day", application_id="BLA000003", public_features_as_of=decision),
        valid,
    ]
    assert [x.case_id for x in match_historical_cases(TARGET, records)] == ["valid"]


def test_prior_outcome_must_be_public_at_prediction_cutoff():
    decision = AS_OF - timedelta(days=10)
    evidence = AS_OF + timedelta(days=1)
    assert match_historical_cases(TARGET, [record("late_release", decision, evidence)]) == []


def test_csv_schema_or_pdf_download_cannot_self_adjudicate():
    decision = AS_OF - timedelta(days=10)
    case = record("unreviewed", decision, decision, adjudicated=False)
    assert match_historical_cases(TARGET, [case]) == []
    # Old call sites omit both new gates and also fail closed.
    legacy = HistoricalCase(
        "legacy", "lung cancer", "oncology", "antibody", 3,
        decision, "APPROVED", decision, "https://www.fda.gov/example",
    )
    assert match_historical_cases(TARGET, [legacy]) == []


def test_duplicate_case_ids_are_all_excluded_to_avoid_double_count():
    decision = AS_OF - timedelta(days=10)
    rows = [
        record("duplicated", decision, decision),
        record("duplicated", decision, decision + timedelta(days=1)),
        record("unique", decision, decision),
    ]
    assert [x.case_id for x in match_historical_cases(TARGET, rows)] == ["unique"]


def test_rejects_credentials_ports_fragments_and_fake_official_sources():
    decision = AS_OF - timedelta(days=10)
    bad_urls = (
        "https://www.fda.gov@evil.test/example",
        "https://www.fda.gov:8443/example",
        "https://www.fda.gov/example#frag",
        "http://www.fda.gov/example",
        "https://www.fda.gov/",
    )
    for index, url in enumerate(bad_urls):
        assert match_historical_cases(TARGET, [record(f"fake-{index}", decision, decision, url=url)]) == []


def test_limit_still_applies_and_comparators_never_enable_probability():
    decision = AS_OF - timedelta(days=10)
    rows = [record(f"case-{i}", decision, decision) for i in range(5)]
    matches = match_historical_cases(TARGET, rows, limit=2)
    assert len(matches) == 2
    assert prediction_status(matches)["probability"] is None


@pytest.mark.parametrize("bad_metadata", [
    {"outcome":"COMPLETE_RESPONSE"}, {"source_url":"https://example.org/claim"},
    {"independently_adjudicated":False}, {"evidence_as_of":None},
])
def test_exact_cycle_duplicates_quarantine_all_claims_before_quality_filtering(bad_metadata):
    decision = AS_OF - timedelta(days=10)
    first = record("local-id-one", decision, decision)
    other = replace(first, case_id="different-local-id", **bad_metadata)
    for rows in ([first,other], [other,first]):
        assert match_historical_cases(TARGET, rows) == []


def test_application_id_format_alias_cannot_bypass_cycle_deduplication():
    decision = AS_OF - timedelta(days=10)
    first = replace(record("one", decision, decision), application_id="NDA000001")
    other = replace(first, case_id="two", application_id=" nda-000001 ")
    assert match_historical_cases(TARGET, [first,other]) == []


@pytest.mark.parametrize("application,cycle", [(None,1),("invented",1),("NDA000001",True),("NDA000001",0)])
def test_missing_or_invalid_exact_identity_cannot_enter_comparator_pool(application,cycle):
    decision = AS_OF - timedelta(days=10)
    case = replace(record("identity",decision,decision), application_id=application,review_cycle=cycle)
    assert match_historical_cases(TARGET,[case]) == []


def test_same_day_outcome_evidence_is_not_known_at_an_earlier_prediction_time():
    decision = AS_OF - timedelta(days=10)
    assert match_historical_cases(TARGET,[record("same-day",decision,AS_OF)]) == []
