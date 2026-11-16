import copy

from assessment_levels_07_20.prediction_ledger import validate_prediction_ledger


def sample():
    return [{"nct_id": "NCT12345678", "application_id": "NDA123456",
             "indication": "Example", "level": 7, "frozen_on": "2024-01-01",
             "predicted_on": "2024-01-05", "cutoff_on": "2024-02-01",
             "decision_on": "2024-04-01", "snapshot_sha256": "a" * 64,
             "prediction_sha256": "b" * 64, "prediction": "ABSTAIN",
             "scientific_status": "NOT_VERIFIED"}]


def test_abstention_ledger_valid_without_accuracy_claim():
    records = sample()
    before = copy.deepcopy(records)
    result = validate_prediction_ledger(records)
    assert result["ledger_ready_for_independent_review"]
    assert result["accuracy_evaluated"] is False
    assert records == before


def test_post_cutoff_prediction_rejected():
    records = sample()
    records[0]["predicted_on"] = "2024-02-01"
    assert "RECORD_0_TEMPORAL_LEAKAGE" in validate_prediction_ledger(records)["errors"]


def test_nested_outcome_rejected():
    records = sample()
    records[0]["metadata"] = {"history": [{"fda_decision": "approved"}]}
    assert "RECORD_0_OUTCOME_LEAKAGE" in validate_prediction_ledger(records)["errors"]


def test_duplicate_event_level_rejected():
    records = sample()
    assert "RECORD_1_DUPLICATE_EVENT_LEVEL" in validate_prediction_ledger(records * 2)["errors"]


def test_unverified_prediction_rejected():
    records = sample()
    records[0]["prediction"] = "APPROVE"
    assert "RECORD_0_UNVERIFIED_PREDICTION" in validate_prediction_ledger(records)["errors"]


def test_invalid_hash_and_level_rejected():
    records = sample()
    records[0]["prediction_sha256"] = "missing"
    records[0]["level"] = 3
    result = validate_prediction_ledger(records)
    assert "RECORD_0_INVALID_PREDICTION_SHA256" in result["errors"]
    assert "RECORD_0_INVALID_LEVEL" in result["errors"]
