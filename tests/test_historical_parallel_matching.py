"""Synthetic software regressions, never independently validated FDA accuracy."""
from datetime import date, datetime

import pytest

from scripts.historical_parallel_matching import find_parallels


def current(**changes):
    return {"program_id": "target", "application_id": "NDA999999",
            "indication": "condition", "mechanism": "mechanism", **changes}


def historical(**changes):
    return {"program_id": "historical-trial", "application_id": "NDA123456",
            "submission_id": "ORIG1", "review_cycle": 1,
            "indication": "condition", "mechanism": "mechanism",
            "fda_outcome": "crl", "fda_decision_date": "2020-02-01",
            "public_features_as_of": "2020-01-01", "evidence_as_of": "2020-03-01",
            "source_urls": ["https://clinicaltrials.gov/study/NCT00000001"],
            "outcome_source_url": "https://www.fda.gov/media/example/download", **changes}


def retrieve(rows, **kwargs):
    return find_parallels(current(), rows, as_of="2021-01-01", **kwargs)


def test_urls_hashes_or_review_flags_never_self_certify_original_source_truth():
    result = retrieve([historical(independently_verified=True, source_content_verified=True,
                                  independentlyReviewed=True, full_document_sha256="a" * 64)])
    assert result["status"] == "unverified_candidates_available"
    assert result["candidate_match_count"] == 1
    assert result["verified_match_count"] == 0
    assert result["prediction_probability"] is None
    assert result["model_validated"] is False
    match = result["matches"][0]
    assert match["candidate_fda_outcome"] == "crl"
    assert match["fda_outcome"] is None
    assert match["source_content_verified"] is False
    assert match["independently_verified"] is False
    assert match["model_eligible"] is False
    assert match["match_status"] == "unscored"
    assert result["historical_parallels_collapsed"] is True


@pytest.mark.parametrize("changes", [
    {"public_features_as_of": "2020-02-01"},
    {"public_features_as_of": "2020-02-02"},
    {"evidence_as_of": "2020-01-31"},
    {"evidence_as_of": "2021-01-01"},
    {"fda_decision_date": "2021-01-01", "evidence_as_of": "2021-01-01"},
    {"fda_decision_date": "2022-01-01", "evidence_as_of": "2022-01-02"},
    {"public_features_as_of": None},
    {"evidence_as_of": None},
])
def test_separate_features_and_outcome_chronology_blocks_leakage(changes):
    result = retrieve([historical(**changes)])
    assert result["matches"] == []
    assert result["candidate_review_cycle_count"] == 0


def test_decision_day_outcome_publication_is_valid_candidate_not_predecision_feature():
    result = retrieve([historical(evidence_as_of="2020-02-01")])
    assert result["candidate_match_count"] == 1
    assert result["matches"][0]["public_features_as_of"] == "2020-01-01"
    assert result["matches"][0]["outcome_evidence_as_of"] == "2020-02-01"


@pytest.mark.parametrize("field,value", [
    ("evidence_as_of", "2020-03-01T23:59:59Z"),
    ("public_features_as_of", "2020-01-01junk"),
    ("fda_decision_date", "2020-02-30"),
    ("fda_decision_date", "20200201"),
    ("evidence_as_of", 20200301),
    ("public_features_as_of", datetime(2020, 1, 1)),
])
def test_malformed_historical_dates_excluded_without_crashing(field, value):
    result = retrieve([historical(**{field: value}), historical(program_id="valid")])
    assert result["candidate_match_count"] == 1
    assert result["matches"][0]["program_id"] == "valid"


@pytest.mark.parametrize("as_of", ["2021-01-01T00:00:00Z", "2021-02-30", "20210101", None, 20210101])
def test_invalid_target_cutoff_is_not_silently_truncated(as_of):
    with pytest.raises(ValueError, match="as_of"):
        find_parallels(current(), [], as_of=as_of)


def test_date_objects_remain_supported_without_accepting_datetime_subclass():
    result = find_parallels(current(), [historical(public_features_as_of=date(2020, 1, 1))],
                            as_of=date(2021, 1, 1))
    assert result["candidate_match_count"] == 1


@pytest.mark.parametrize("changes", [
    {"application_id": "not-an-application"}, {"application_id": None},
    {"review_cycle": None}, {"review_cycle": True}, {"review_cycle": 0},
    {"review_cycle": "1"}, {"submission_id": None}, {"submission_id": ""},
    {"outcome_source_url": "https://example.com/fda-letter.pdf"},
    {"outcome_source_url": "https://www.fda.gov.evil.example/letter"},
])
def test_exact_identity_and_official_outcome_citation_required(changes):
    assert retrieve([historical(**changes)])["matches"] == []


@pytest.mark.parametrize("url", [
    "http://www.fda.gov/letter", "https://user:pass@www.fda.gov/letter",
    "https://www.fda.gov:443/letter", "https://www.fda.gov/letter#fragment",
    "https://www.fda.gov/letter\n", "file:///tmp/letter", "not a url",
])
def test_unsafe_source_urls_are_excluded(url):
    assert retrieve([historical(source_urls=[url])])["matches"] == []
    assert retrieve([historical(outcome_source_url=url)])["matches"] == []


@pytest.mark.parametrize("sources", ["https://www.fda.gov/letter", [], None, [None]])
def test_source_list_is_not_a_string_or_missing(sources):
    assert retrieve([historical(source_urls=sources)])["matches"] == []


def test_multiple_trials_and_application_aliases_count_one_cycle():
    result = retrieve([historical(program_id="NCT1", application_id="nda-123456"),
                       historical(program_id="NCT2", application_id="NDA 123456")])
    assert result["candidate_match_count"] == 1
    assert result["candidate_application_count"] == 1
    assert result["candidate_review_cycle_count"] == 1
    assert result["matches"][0]["associated_program_ids"] == ["NCT1", "NCT2"]
    assert result["matches"][0]["application_id"] == "NDA123456"


def test_crl_then_later_approval_are_distinct_cycles_same_application():
    result = retrieve([historical(), historical(program_id="resubmission-trial", review_cycle=2,
                       fda_outcome="approved", fda_decision_date="2020-10-01",
                       public_features_as_of="2020-08-01", evidence_as_of="2020-10-01")])
    assert result["candidate_review_cycle_count"] == 2
    assert result["candidate_application_count"] == 1
    assert result["conflicting_review_cycle_count"] == 0
    assert {m["candidate_fda_outcome"] for m in result["matches"]} == {"crl", "approved"}


def test_original_and_supplement_cycles_are_not_conflated():
    result = retrieve([historical(), historical(program_id="supplement", submission_id="SUPPL001")])
    assert result["candidate_review_cycle_count"] == 2
    assert result["candidate_application_count"] == 1


@pytest.mark.parametrize("changes", [
    {"fda_outcome": "approved"},
    {"fda_decision_date": "2020-02-02"},
])
def test_conflicting_cycle_excluded_even_when_opposing_row_has_no_matching_dimensions(changes):
    result = retrieve([historical(), historical(program_id="opposing", indication="different",
                       mechanism="different", **changes)])
    assert result["conflicting_review_cycle_count"] == 1
    assert result["candidate_match_count"] == 0


def test_future_or_unknown_fda_outcomes_never_reclassified_as_development():
    for action in ["pending", "delayed", "resubmitted", "trial_failed", "", "unknown"]:
        assert retrieve([historical(fda_outcome=action)])["matches"] == []
    result = retrieve([historical(fda_outcome="no_application", application_id=None)])
    assert result["matches"][0]["group"] == "development_candidate"
    assert result["matches"][0]["candidate_fda_outcome"] is None
    assert result["candidate_review_cycle_count"] == 0


def test_same_target_application_excluded_even_with_different_program():
    assert retrieve([historical(application_id="NDA-999999")])["matches"] == []
    assert retrieve([historical(program_id="target")])["matches"] == []


def test_limits_describe_actual_truncation_and_counts_use_complete_candidate_pool():
    rows = [historical(program_id=str(n), application_id=f"NDA{123450+n}") for n in range(3)]
    limited = retrieve(rows, limit=2)
    assert limited["candidate_match_count"] == 2
    assert limited["total_candidate_count"] == 3
    assert limited["candidate_application_count"] == 3
    assert limited["match_count_is_limited"] is True
    assert retrieve(rows, limit=3)["match_count_is_limited"] is False


@pytest.mark.parametrize("limit", [True, 1.5, 0, 101])
def test_invalid_limits_rejected(limit):
    with pytest.raises(ValueError, match="limit"):
        retrieve([], limit=limit)


def test_no_outcome_or_probability_used_to_rank_similarities():
    first = historical(program_id="a", fda_outcome="crl", predicted_probability=.99)
    second = historical(program_id="b", application_id="NDA123457", fda_outcome="approved",
                        predicted_probability=.01)
    assert [m["program_id"] for m in retrieve([second, first])["matches"]] == ["a", "b"]
    assert [m["program_id"] for m in retrieve([first, second])["matches"]] == ["a", "b"]


def test_non_mapping_record_diagnosed_and_does_not_crash_batch():
    result = retrieve([None, historical()])
    assert result["candidate_match_count"] == 1
    assert result["excluded_record_counts"]["invalid_record"] == 1


@pytest.mark.parametrize("revision", [
    "rescinded_crl", "rescind_complete_response", "corrected_complete_response",
    "corrected_crl", "corrected_provisional_determination", "rescinded_approval",
    "corrected_approval", "rescission", "correction",
])
def test_revision_claim_quarantines_dependent_cycle_before_feature_matching(revision):
    # Revision action provenance is independent from clinical comparison features.
    revised = historical(program_id="revision", fda_outcome=revision,
                         fda_decision_date="2020-04-01", evidence_as_of="2020-04-02",
                         indication="unrelated", mechanism="different",
                         public_features_as_of=None, source_urls=None)
    result = retrieve([historical(), revised])
    assert result["matches"] == []
    assert result["revision_dependent_review_cycle_count"] == 1
    assert result["excluded_record_counts"]["prior_action_adjudication_required"] == 1
    assert result["verified_match_count"] == 0


@pytest.mark.parametrize("changes", [
    {"fda_decision_date": "2021-01-01", "evidence_as_of": "2021-01-01"},
    {"fda_decision_date": "2021-02-01", "evidence_as_of": "2021-02-02"},
    {"evidence_as_of": "2021-01-01"},
    {"evidence_as_of": "2020-01-01"},
    {"evidence_as_of": None},
    {"fda_decision_date": "2020-02-30"},
    {"outcome_source_url": "https://example.com/unverified-revision"},
    {"review_cycle": None},
    {"submission_id": None},
])
def test_invalid_or_postcutoff_revision_does_not_contaminate_earlier_cutoff(changes):
    revised = historical(program_id="revision", fda_outcome="rescinded_crl",
                         fda_decision_date="2020-04-01", evidence_as_of="2020-04-02")
    revised.update(changes)
    result = retrieve([historical(), revised])
    assert result["candidate_match_count"] == 1
    assert result["revision_dependent_review_cycle_count"] == 0


@pytest.mark.parametrize("changes", [
    {"review_cycle": 2}, {"submission_id": "SUPPL001"}, {"application_id": "NDA123457"},
])
def test_revision_of_different_exact_cycle_does_not_suppress_unrelated_candidate(changes):
    revised = historical(program_id="revision", fda_outcome="corrected_crl",
                         fda_decision_date="2020-04-01", evidence_as_of="2020-04-02",
                         **changes)
    result = retrieve([historical(), revised])
    assert result["candidate_match_count"] == 1
    assert result["revision_dependent_review_cycle_count"] == 0


def test_revision_quarantines_only_earlier_crl_cycle_and_keeps_later_approval_cycle():
    revised = historical(program_id="revision", fda_outcome="rescinded_crl",
                         fda_decision_date="2020-04-01", evidence_as_of="2020-04-02")
    later = historical(program_id="later", review_cycle=2, fda_outcome="approved",
                       fda_decision_date="2020-10-01", public_features_as_of="2020-08-01",
                       evidence_as_of="2020-10-02")
    result = retrieve([historical(), later, revised])
    assert result["candidate_match_count"] == 1
    assert result["matches"][0]["candidate_fda_outcome"] == "approved"
    assert result["matches"][0]["review_cycle"] == 2
    assert result["revision_dependent_review_cycle_count"] == 1
