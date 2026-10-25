import json
from pathlib import Path
from app.hop_status import hop_readiness_status

def test_staging_never_claims_prediction_ready():
    result = hop_readiness_status()
    assert result["historical_staged"] >= 1
    assert result["historical_model_eligible"] == 0
    assert result["model_validated"] is False
    assert result["prediction_probability"] is None

def test_staging_flag_cannot_promote_to_training(tmp_path: Path):
    path = tmp_path / "staging.json"
    path.write_text(json.dumps({"records":[{"model_eligible": True}]}))
    result = hop_readiness_status(path)
    assert result["historical_model_eligible"] == 0
    assert result["historical_quarantined"] == 1
    assert result["prediction_available"] is False

def test_missing_staging_fails_closed(tmp_path: Path):
    result = hop_readiness_status(tmp_path / "missing.json")
    assert result["status"] == "SOURCE_UNAVAILABLE"
    assert result["prediction_probability"] is None

def test_missing_and_malformed_eligibility_flags_stay_quarantined(tmp_path: Path):
    path = tmp_path / "staging.json"
    path.write_text(json.dumps({"records": [{}, {"model_eligible": "true"}, None]}))
    result = hop_readiness_status(path)
    assert result["historical_staged"] == 3
    assert result["historical_quarantined"] == 3
    assert result["historical_model_eligible"] == 0
    assert result["prediction_probability"] is None
