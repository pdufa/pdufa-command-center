import copy

import pytest

from assessment_levels_07_20.point_in_time_evidence import validate_point_in_time_evidence


def sample():
    return {
        "nct_id": "NCT01234567",
        "cutoff_on": "2026-05-01",
        "evidence": [{
            "nct_id": "NCT01234567",
            "source_url": "https://clinicaltrials.gov/study/NCT01234567",
            "sha256": "a" * 64,
            "published_on": "2026-04-20",
            "retrieved_on": "2026-04-21",
        }],
    }


def test_valid_provenance_is_only_review_eligible_not_scored():
    record = sample()
    before = copy.deepcopy(record)
    result = validate_point_in_time_evidence(record)
    assert result["eligible_for_owner_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"
    assert record == before


@pytest.mark.parametrize("field,value,expected", [
    ("published_on", "2026-05-01", "NOT_BEFORE_CUTOFF_PUBLISHED_ON"),
    ("retrieved_on", "2026-05-02", "NOT_BEFORE_CUTOFF_RETRIEVED_ON"),
    ("published_on", "2026-02-30", "INVALID_PUBLISHED_ON"),
    ("retrieved_on", "2026-04-21T12:00:00Z", "INVALID_RETRIEVED_ON"),
    ("nct_id", "NCT99999999", "TRIAL_MISMATCH"),
    ("source_url", "http://example.org", "INVALID_SOURCE"),
    ("source_url", "https://user:secret@example.org/a", "INVALID_SOURCE"),
    ("sha256", "unverified", "INVALID_HASH"),
])
def test_invalid_evidence_fails_closed(field, value, expected):
    record = sample()
    record["evidence"][0][field] = value
    result = validate_point_in_time_evidence(record)
    assert not result["eligible_for_owner_review"]
    assert any(expected in error for error in result["errors"])
    assert result["fda_prediction"] == "ABSTAIN"


def test_missing_or_invalid_evidence_fails_closed():
    for evidence in ([], None, [None]):
        record = sample()
        record["evidence"] = evidence
        assert not validate_point_in_time_evidence(record)["eligible_for_owner_review"]


def test_invalid_cutoff_fails_closed():
    record = sample()
    record["cutoff_on"] = "not-a-date"
    assert "INVALID_CUTOFF" in validate_point_in_time_evidence(record)["errors"]


def test_nonmapping_rejected():
    with pytest.raises(TypeError):
        validate_point_in_time_evidence(None)


def test_reject_evidence_published_after_retrieval():
    record = sample()
    record["evidence"][0]["published_on"] = "2026-04-22"
    result = validate_point_in_time_evidence(record)
    assert not result["eligible_for_owner_review"]
    assert "EVIDENCE_0_PUBLISHED_AFTER_RETRIEVAL" in result["errors"]


def test_reject_nested_outcome_leakage():
    record = sample()
    record["evidence"][0]["fda_outcome"] = "approved"
    result = validate_point_in_time_evidence(record)
    assert not result["eligible_for_owner_review"]
    assert "EVIDENCE_0_OUTCOME_LEAKAGE" in result["errors"]
    assert result["fda_prediction"] == "ABSTAIN"
