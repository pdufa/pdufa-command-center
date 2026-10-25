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


def test_real_published_fda_archive_reported_as_source_only():
    result = hop_readiness_status()
    source = result["published_crl_source"]
    assert source["published_letter_records"] == 458
    assert source["quarantined_letter_records"] == 458
    assert source["fda_export_date"] == "2026-10-21"
    assert source["model_eligible_records"] == 0
    assert source["complete_denominator_verified"] is False
    assert result["prediction_probability"] is None


def test_false_cohort_completeness_or_count_mismatch_fails_closed(tmp_path: Path):
    audit = {
        "status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
        "published_letter_records": 2, "quarantined_letter_records": 2,
        "letter_type_counts": {"COMPLETE RESPONSE": 2},
        "verified_complete_application_denominator": False,
        "model_eligible_records": 0, "verified_application_review_cycles": 0,
        "source_export_date": "2026-10-21", "collection_run_url": "https://github.com/example",
    }
    p = tmp_path / "audit.json"
    p.write_text(json.dumps(audit))
    assert hop_readiness_status(source_audit_path=p)["published_crl_source"]["published_letter_records"] == 2
    audit["verified_complete_application_denominator"] = True
    p.write_text(json.dumps(audit))
    assert hop_readiness_status(source_audit_path=p)["published_crl_source"] is None
    audit["verified_complete_application_denominator"] = False
    audit["letter_type_counts"]["COMPLETE RESPONSE"] = 3
    p.write_text(json.dumps(audit))
    assert hop_readiness_status(source_audit_path=p)["published_crl_source"] is None
    assert hop_readiness_status(source_audit_path=p)["prediction_available"] is False
