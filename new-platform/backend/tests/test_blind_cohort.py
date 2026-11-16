import copy

import pytest

from assessment_levels_07_20.blind_cohort import validate_blind_cohort


def sample():
    return {"trials": [{
        "nct_id": "NCT01234567",
        "application_id": "NDA-123456",
        "indication": "Example indication",
        "frozen_on": "2026-01-01",
        "cutoff_on": "2026-02-01",
        "decision_on": "2026-03-01",
        "snapshot_sha256": "b" * 64,
    }]}


def test_valid_manifest_only_enables_blind_review():
    manifest = sample()
    before = copy.deepcopy(manifest)
    result = validate_blind_cohort(manifest)
    assert result["eligible_for_blind_review"]
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["scientific_score"] is None
    assert result["fda_prediction"] == "ABSTAIN"
    assert manifest == before


@pytest.mark.parametrize("field,value,expected", [
    ("cutoff_on", "2026-01-01", "TEMPORAL_LEAKAGE"),
    ("decision_on", "2026-02-01", "TEMPORAL_LEAKAGE"),
    ("frozen_on", "2026-03-01", "TEMPORAL_LEAKAGE"),
    ("decision_on", "invalid", "INVALID_DATES"),
    ("snapshot_sha256", "missing", "INVALID_SNAPSHOT_HASH"),
    ("nct_id", "bad", "INVALID_NCT"),
    ("application_id", "", "MISSING_APPLICATION"),
    ("indication", " ", "MISSING_INDICATION"),
    ("fda_outcome", "APPROVED", "OUTCOME_LEAKAGE"),
    ("actual_decision", "REJECTED", "OUTCOME_LEAKAGE"),
    ("approval_status", "approved", "OUTCOME_LEAKAGE"),
    ("outcome_label", 1, "OUTCOME_LEAKAGE"),
])
def test_invalid_manifest_rejected(field, value, expected):
    manifest = sample()
    manifest["trials"][0][field] = value
    result = validate_blind_cohort(manifest)
    assert not result["eligible_for_blind_review"]
    assert any(expected in error for error in result["errors"])
    assert result["fda_prediction"] == "ABSTAIN"


def test_duplicate_application_indication_event_rejected():
    manifest = sample()
    manifest["trials"].append(copy.deepcopy(manifest["trials"][0]))
    assert "TRIAL_1_DUPLICATE_EVENT" in validate_blind_cohort(manifest)["errors"]


@pytest.mark.parametrize("trials", [[], None, [None]])
def test_missing_or_malformed_trials_rejected(trials):
    assert not validate_blind_cohort({"trials": trials})["eligible_for_blind_review"]


def test_nonmapping_rejected():
    with pytest.raises(TypeError):
        validate_blind_cohort(None)


def test_nested_fda_outcome_is_rejected():
    manifest = sample()
    manifest["trials"][0]["source_metadata"] = {"history": [{"fda_decision": "approved"}]}
    result = validate_blind_cohort(manifest)
    assert not result["eligible_for_blind_review"]
    assert "TRIAL_0_OUTCOME_LEAKAGE" in result["errors"]


def test_manifest_level_outcome_is_rejected():
    manifest = sample()
    manifest["metadata"] = {"decision_result": "approved"}
    result = validate_blind_cohort(manifest)
    assert not result["eligible_for_blind_review"]
    assert "MANIFEST_OUTCOME_LEAKAGE" in result["errors"]
