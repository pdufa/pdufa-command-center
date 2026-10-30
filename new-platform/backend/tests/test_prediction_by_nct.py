import pytest
from app.prediction_by_nct import prediction_payload


def test_valid_nct_populates_only_matching_dossier():
    payload = prediction_payload("NCT01234567", {"nct_id": "NCT01234567", "sponsor": {"name": "Test"}})
    assert payload["nct_id"] == "NCT01234567"
    assert payload["dossier"]["sponsor"]["name"] == "Test"
    assert payload["decision"] == "ABSTAIN"
    assert not payload["prediction_authorized"]
    assert len(payload["headline_metrics"]) == 12
    assert len(payload["supporting_metrics"]) == 48
    assert len(payload["scientific_assessments"]) == 40


def test_mismatched_trial_is_rejected():
    with pytest.raises(ValueError, match="mismatch"):
        prediction_payload("NCT01234567", {"nct_id": "NCT07654321"})


def test_missing_dossier_is_rejected():
    with pytest.raises(LookupError):
        prediction_payload("NCT01234567", None)


def test_invalid_identifier_is_rejected():
    with pytest.raises(ValueError, match="Invalid"):
        prediction_payload("NCT-123", {"nct_id": "NCT-123"})
