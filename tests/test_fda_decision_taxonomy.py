"""Synthetic contract regressions; not FDA evidence or measured model accuracy."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fda_decision_taxonomy import classify_decision, deduplicate_applications


def event(action="approval", **changes):
    return {"application_id": "NDA123456", "submission_id": "ORIG-000",
            "review_cycle": 1, "action": action, "decision_date": "2020-01-01",
            "evidence_as_of": "2020-01-02", "retrieved_on": "2020-01-03",
            "source_url": "https://www.accessdata.fda.gov/example", **changes}


@pytest.mark.parametrize("action,label", [("approval", "PASS"), ("accelerated_approval", "PASS"),
                                         ("traditional approval", "PASS"), ("crl", "FAIL"),
                                         ("complete_response_letter", "FAIL")])
def test_binary_actions_are_candidates_only(action, label):
    result = classify_decision(event(action), as_of="2020-02-01")
    assert result["candidate_label"] == label
    assert result["label"] is None
    for field in ("eligible_for_binary_training", "model_eligible", "independently_verified",
                  "source_content_verified"):
        assert result[field] is False


@pytest.mark.parametrize("extra", [{"source_content_verified": True, "independently_verified": True,
                                   "eligible_for_binary_training": True, "model_eligible": True},
                                  {"source_document_sha256": "a"*64,
                                   "reviewer_one": "Alice", "reviewer_two": "Bob"}])
def test_caller_assertions_cannot_promote_candidate(extra):
    result = classify_decision(event(**extra), as_of="2020-02-01")
    assert result["label"] is None and result["model_eligible"] is False
    assert result["independently_verified"] is False


@pytest.mark.parametrize("app", ["nda-123456", "NDA 123456", "NDA123456"])
def test_canonical_identity(app):
    assert classify_decision(event(application_id=app), as_of="2020-02-01")["application_id"] == "NDA123456"


@pytest.mark.parametrize("changes", [{"application_id": "123456"}, {"application_id": "NDA123"},
    {"application_id": "NDA1234567"}, {"application_id": True}, {"application_id": "BL125807/0"},
    {"review_cycle": None}, {"review_cycle": True}, {"review_cycle": 0}, {"review_cycle": 1.0},
    {"review_cycle": "1.0"}, {"submission_id": ""}, {"submission_id": "x\ny"}])
def test_exact_cycle_required(changes):
    result = classify_decision(event(**changes), as_of="2020-02-01")
    assert result["status"] == "missing_exact_application_submission_cycle"
    assert result["candidate_label"] is None


def test_csv_cycle_string():
    assert classify_decision(event(review_cycle="1"), as_of="2020-02-01")["review_cycle"] == 1


@pytest.mark.parametrize("url", ["", "https://example.com/fda", "http://www.fda.gov/docs",
    "https://www.fda.gov.evil.test/doc", "https://x@www.fda.gov/doc",
    "https://www.fda.gov:443/doc", "https://www.fda.gov/doc#fragment", "https://www.fda.gov/",
    "https://www.fda.gov/d oc", "https://[bad"])
def test_official_url_is_required_but_not_verification(url):
    result = classify_decision(event(source_url=url), as_of="2020-02-01")
    assert "official_fda_source_required" in result["issues"]
    assert result["eligible_for_binary_training"] is False


@pytest.mark.parametrize("changes", [{"decision_date": "2020-01-32"}, {"decision_date": "20200101"},
    {"decision_date": "2020-01-01T12:00:00Z"}, {"evidence_as_of": None}, {"retrieved_on": None},
    {"evidence_as_of": "2019-12-31"}, {"evidence_as_of": "2020-02-02"},
    {"retrieved_on": "2020-01-01"}, {"retrieved_on": "2020-02-02"}])
def test_distinct_action_publication_retrieval_chronology(changes):
    result = classify_decision(event(**changes), as_of="2020-02-01")
    assert result["candidate_label"] is None
    assert result["issues"]


def test_future_action_excluded():
    assert "future_event_excluded" in classify_decision(event(), as_of="2019-12-31")["issues"]


@pytest.mark.parametrize("as_of", ["20200101", "2020-02-30", "2020-01-01T00:00:00Z", None])
def test_invalid_cutoff_fails(as_of):
    with pytest.raises(ValueError):
        classify_decision(event(), as_of=as_of)


@pytest.mark.parametrize("action", ["withdrawn", "delayed", "pending", "resubmitted", "rtf",
                                    "tentative_approval", "unresolved"])
def test_nonbinary_censoring(action):
    result = classify_decision(event(action), as_of="2020-02-01")
    assert result["status"] == "censored_or_out_of_scope"
    assert result["candidate_label"] is None


def test_unknown_action_requires_review():
    assert classify_decision(event("unclear"), as_of="2020-02-01")["status"] == "unknown_action_requires_review"


def test_duplicate_trials_and_canonical_aliases_count_once():
    result = deduplicate_applications([event(), event(application_id="nda-123456")], as_of="2020-02-01")
    assert result["counts"]["candidate_review_cycles"] == 1
    assert result["counts"]["verified_applications"] == 0
    assert result["accepted"] == []


def test_crl_then_later_approval_are_distinct_review_cycles():
    result = deduplicate_applications([event("crl"), event(review_cycle=2, decision_date="2020-01-10",
                                    evidence_as_of="2020-01-10", retrieved_on="2020-01-11")], as_of="2020-02-01")
    assert result["counts"]["candidate_review_cycles"] == 2
    assert result["counts"]["candidate_applications"] == 1
    assert result["counts"]["candidate_pass"] == result["counts"]["candidate_fail"] == 1
    assert result["counts"]["conflicting_review_cycles"] == 0
    assert result["counts"]["verified_pass"] == result["counts"]["verified_fail"] == 0


@pytest.mark.parametrize("other", [event("crl"), event(decision_date="2020-01-02")])
def test_conflicting_labels_or_dates_quarantine_entire_cycle(other):
    result = deduplicate_applications([event(), other], as_of="2020-02-01")
    assert result["counts"]["conflicting_review_cycles"] == 1
    assert result["counts"]["candidate_review_cycles"] == 0


def test_supplements_are_distinct_explicit_submissions():
    result = deduplicate_applications([event(), event(submission_id="SUPPL-001")], as_of="2020-02-01")
    assert result["counts"]["candidate_review_cycles"] == 2


def test_invalid_row_shape_quarantines():
    assert classify_decision([], as_of="2020-02-01")["status"] == "invalid_event"


@pytest.mark.parametrize("action", ["rescinded_crl", "rescind_complete_response",
    "corrected_crl", "corrected_complete_response", "corrected_provisional_determination",
    "rescinded_approval", "corrected_approval", "rescission", "correction"])
def test_revisions_require_prior_action_adjudication(action):
    revision = event(action, decision_date="2020-01-10", evidence_as_of="2020-01-11",
                     retrieved_on="2020-01-12")
    classification = classify_decision(revision, as_of="2020-02-01")
    assert classification["status"] == "prior_action_adjudication_required"
    assert classification["candidate_label"] is None
    result = deduplicate_applications([event("crl"), revision], as_of="2020-02-01")
    assert result["counts"]["candidate_fail"] == 0
    assert result["counts"]["candidate_review_cycles"] == 0
    assert result["counts"]["revision_dependent_review_cycles"] == 1
    assert result["counts"]["verified_fail"] == 0
    dependency = result["revision_dependent_review_cycles"][0]
    assert dependency["binary_observations"][0]["decision_date"] == "2020-01-01"
    assert dependency["binary_observations"][0]["evidence_as_of"] == "2020-01-02"
    assert dependency["revision_observations"][0]["decision_date"] == "2020-01-10"
    assert dependency["revision_observations"][0]["evidence_as_of"] == "2020-01-11"
    assert dependency["revision_observations"][0]["retrieved_on"] == "2020-01-12"


@pytest.mark.parametrize("changes", [{"review_cycle": 2}, {"submission_id": "SUPPL-001"},
                                     {"application_id": "BLA123456"}])
def test_revision_different_exact_cycle_does_not_suppress_unrelated_claim(changes):
    result = deduplicate_applications([event("crl"), event("rescinded_crl", **changes)], as_of="2020-02-01")
    assert result["counts"]["candidate_fail"] == 1
    assert result["counts"]["revision_dependent_review_cycles"] == 0


@pytest.mark.parametrize("action", ["resubmitted", "delayed", "pending"])
def test_ordinary_nonbinary_events_do_not_imply_revision(action):
    result = deduplicate_applications([event("crl"), event(action)], as_of="2020-02-01")
    assert result["counts"]["candidate_fail"] == 1
    assert result["counts"]["revision_dependent_review_cycles"] == 0


@pytest.mark.parametrize("changes", [{"decision_date": "2020-02-02"},
    {"evidence_as_of": "2020-02-02", "retrieved_on": "2020-02-03"},
    {"retrieved_on": "2020-02-02"}, {"source_url": "https://example.com/doc"},
    {"evidence_as_of": None}])
def test_revision_not_available_by_cutoff_does_not_rewrite_past_candidate(changes):
    result = deduplicate_applications([event("crl"), event("rescinded_crl", **changes)], as_of="2020-02-01")
    assert result["counts"]["candidate_fail"] == 1
    assert result["counts"]["revision_dependent_review_cycles"] == 0


def test_unknown_action_still_requires_classification_not_binary_promotion():
    result = deduplicate_applications([event("unrecognized_correction_kind")], as_of="2020-02-01")
    assert result["counts"]["candidate_review_cycles"] == 0
    assert result["excluded"][0]["status"] == "unknown_action_requires_review"
