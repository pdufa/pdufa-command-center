"""Research-only comparator tests; cases are synthetic, not FDA decisions."""
from dataclasses import replace
from datetime import date, timedelta
from itertools import count

import pytest

from app.hop_comparators import HistoricalCase, TargetCase, match_historical_cases, prediction_status

AS_OF = date(2026, 10, 25)
TARGET = TargetCase("lung cancer", "oncology", "antibody", 3, AS_OF)
SYNTHETIC_APPLICATION_IDS = count(900000)


def record(case_id, decision, evidence, outcome="APPROVED", url="https://www.fda.gov/example", *,
           features=None, adjudicated=True, application_id=None, review_cycle=1):
    return HistoricalCase(
        case_id, "lung cancer", "oncology", "antibody", 3, decision, outcome, evidence, url,
        public_features_as_of=features if features is not None else decision - timedelta(days=30),
        independently_adjudicated=adjudicated,
        application_id=application_id or f"NDA{next(SYNTHETIC_APPLICATION_IDS):06d}",
        review_cycle=review_cycle,
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
        replace(valid, case_id="undated", public_features_as_of=None),
        replace(valid, case_id="postdecision", public_features_as_of=decision + timedelta(days=1)),
        replace(valid, case_id="decision_day", public_features_as_of=decision),
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


@pytest.mark.parametrize("changes", [
    {"application_id": None}, {"application_id": ""}, {"application_id": True},
    {"application_id": "NDA123"}, {"application_id": "BL 125807/0"},
    {"application_id": "unknown"}, {"review_cycle": None}, {"review_cycle": 0},
    {"review_cycle": -1}, {"review_cycle": True}, {"review_cycle": "1"},
    {"review_cycle": 1.0},
])
def test_review_flag_cannot_replace_exact_application_and_cycle_identity(changes):
    decision = AS_OF - timedelta(days=10)
    case = replace(record("reviewed", decision, decision), **changes)
    assert case.independently_adjudicated is True
    assert match_historical_cases(TARGET, [case]) == []


def test_repeated_trials_and_application_aliases_count_once_per_exact_review_cycle():
    decision = AS_OF - timedelta(days=10)
    first = record("trial-a", decision, decision, application_id="NDA-123456")
    second = replace(first, case_id="trial-b", application_id="nda123456")
    for rows in ([first, second], [second, first]):
        matches = match_historical_cases(TARGET, rows)
        assert len(matches) == 1
        assert matches[0].case_id == "trial-a"
        assert matches[0].application_id == "NDA123456"
        assert matches[0].review_cycle == 1
        assert prediction_status(matches)["comparator_count"] == 1
        assert prediction_status(matches)["probability"] is None


@pytest.mark.parametrize("changes", [
    {"outcome": "COMPLETE_RESPONSE"},
    {"decision_date": AS_OF - timedelta(days=11)},
    {"outcome": "WITHDRAWN"},
    {"outcome": "RESCINDED_CRL"},
])
def test_conflicting_or_nonbinary_cycle_is_quarantined_before_feature_matching(changes):
    decision = AS_OF - timedelta(days=10)
    first = record("trial-a", decision, decision, application_id="NDA123456")
    # An independently supplied action claim cannot be ranked away because
    # its trial features are missing or less similar to this target.
    opposing = replace(first, case_id="trial-b", public_features_as_of=None,
                       indication="different", modality="different", **changes)
    independent = record("independent-cycle", decision, decision)
    assert [c.case_id for c in match_historical_cases(TARGET, [first, opposing, independent])] == ["independent-cycle"]


def test_crl_and_later_approval_in_distinct_cycles_are_preserved_without_claiming_independence():
    first_date = AS_OF - timedelta(days=200)
    second_date = AS_OF - timedelta(days=10)
    crl = record("crl-cycle", first_date, first_date, "COMPLETE_RESPONSE",
                 application_id="BLA125807", review_cycle=1)
    approval = record("approval-cycle", second_date, second_date, "APPROVED",
                      application_id="BLA125807", review_cycle=2)
    matches = match_historical_cases(TARGET, [crl, approval])
    assert [(c.application_id, c.review_cycle, c.outcome) for c in matches] == [
        ("BLA125807", 2, "APPROVED"), ("BLA125807", 1, "COMPLETE_RESPONSE")]
    assert prediction_status(matches)["status"] == "NOT_VALIDATED"
    assert prediction_status(matches)["probability"] is None


def test_unreviewed_or_postcutoff_claims_do_not_contaminate_prior_reviewed_cycle():
    decision = AS_OF - timedelta(days=10)
    first = record("trial-a", decision, decision, application_id="NDA123456")
    unreviewed = replace(first, case_id="not-adjudicated", outcome="COMPLETE_RESPONSE",
                         independently_adjudicated=False)
    late = replace(first, case_id="future-revision", outcome="RESCINDED_CRL",
                   decision_date=AS_OF + timedelta(days=1), evidence_as_of=AS_OF + timedelta(days=1))
    late_publication = replace(first, case_id="not-yet-public", outcome="COMPLETE_RESPONSE",
                               evidence_as_of=AS_OF + timedelta(days=1))
    assert [c.case_id for c in match_historical_cases(TARGET, [first, unreviewed, late, late_publication])] == ["trial-a"]


def test_case_id_whitespace_cannot_evade_duplicate_guard_across_cycles():
    decision = AS_OF - timedelta(days=10)
    first = record("same-case", decision, decision)
    second = replace(first, case_id=" same-case ", review_cycle=2)
    assert match_historical_cases(TARGET, [first, second]) == []


def test_only_pre_cutoff_source_availability_can_enter_historical_pool():
    decision = AS_OF - timedelta(days=10)
    assert match_historical_cases(TARGET, [record("on-cutoff", decision, AS_OF)]) == []


@pytest.mark.parametrize("changes", [
    {"decision_date": "2020-01-01"}, {"evidence_as_of": None},
    {"public_features_as_of": "2020-01-01"}, {"phase": True}, {"phase": "3"},
    {"phase": 5}, {"indication": ""}, {"therapeutic_area": None}, {"modality": " "},
])
def test_malformed_runtime_metadata_cannot_be_ranked_or_crash_pool(changes):
    decision = AS_OF - timedelta(days=10)
    bad = replace(record("invalid", decision, decision), **changes)
    good = record("valid", decision, decision)
    assert [c.case_id for c in match_historical_cases(TARGET, [bad, good])] == ["valid"]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_limit_requires_positive_integer(limit):
    with pytest.raises(ValueError, match="positive integer"):
        match_historical_cases(TARGET, [], limit=limit)


def test_duplicate_case_rejection_cannot_hide_conflicting_cycle_action_claim():
    decision = AS_OF - timedelta(days=10)
    first = record("duplicated", decision, decision, application_id="NDA123456")
    contradictory_duplicate = replace(first, outcome="COMPLETE_RESPONSE")
    otherwise_unique = replace(first, case_id="another-trial")
    assert match_historical_cases(TARGET, [first, contradictory_duplicate, otherwise_unique]) == []
