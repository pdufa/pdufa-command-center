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


def test_real_approved_registry_and_source_linkage_remain_quarantined():
    result = hop_readiness_status()
    registry = result["approved_registry_source"]
    links = result["fda_identity_crosswalk"]
    assert registry["application_records"] == 29416
    assert registry["application_types"] == {"ANDA": 23023, "BLA": 485, "NDA": 5908}
    assert registry["model_eligible_records"] == 0
    assert registry["complete_denominator_verified"] is False
    assert links["published_letter_records"] == 458
    assert links["identity_link_status_counts"] == {
        "APPLICATION_ID_UNRESOLVED": 15,
        "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS": 2,
        "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT": 107,
        "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT": 334,
    }
    assert links["verified_review_cycle_outcomes"] == 0
    assert links["qualified_reference_letter_records"] == 19
    assert links["unresolved_legacy_bl_letter_records"] == 14
    assert links["letters_without_application_identifiers"] == 1
    assert links["collection_artifact_url"].endswith("/12610973480")
    assert result["prediction_probability"] is None


def test_registry_and_crosswalk_fail_closed_if_counts_are_changed(tmp_path: Path):
    from app.hop_status import DRUGS_SOURCE_AUDIT_PATH, CROSSWALK_AUDIT_PATH
    registry = json.loads(DRUGS_SOURCE_AUDIT_PATH.read_text())
    links = json.loads(CROSSWALK_AUDIT_PATH.read_text())
    rp = tmp_path / "registry.json"
    lp = tmp_path / "links.json"
    rp.write_text(json.dumps(registry))
    lp.write_text(json.dumps(links))
    assert hop_readiness_status(drugs_audit_path=rp, crosswalk_audit_path=lp)["fda_identity_crosswalk"] is not None
    registry["model_eligible_records"] = 1
    rp.write_text(json.dumps(registry))
    result = hop_readiness_status(drugs_audit_path=rp, crosswalk_audit_path=lp)
    assert result["approved_registry_source"] is None
    assert result["fda_identity_crosswalk"] is None
    assert result["prediction_available"] is False
    registry["model_eligible_records"] = 0
    registry["source_application_records"] = 29417
    rp.write_text(json.dumps(registry))
    assert hop_readiness_status(drugs_audit_path=rp)["approved_registry_source"] is None


def test_identity_linkage_cannot_claim_eligible_review_cycles(tmp_path: Path):
    from app.hop_status import CROSSWALK_AUDIT_PATH
    source = json.loads(CROSSWALK_AUDIT_PATH.read_text())
    source["verified_review_cycle_outcomes"] = 329
    path = tmp_path / "links.json"
    path.write_text(json.dumps(source))
    status = hop_readiness_status(crosswalk_audit_path=path)
    assert status["fda_identity_crosswalk"] is None
    assert status["model_validated"] is False


def test_unresolved_or_qualified_source_counts_cannot_exceed_audit_totals(tmp_path: Path):
    from app.hop_status import CROSSWALK_AUDIT_PATH
    src = json.loads(CROSSWALK_AUDIT_PATH.read_text())
    path = tmp_path / "crosswalk.json"
    src["unresolved_legacy_bl_letter_records"] = 16
    path.write_text(json.dumps(src))
    assert hop_readiness_status(crosswalk_audit_path=path)["fda_identity_crosswalk"] is None
    src["unresolved_legacy_bl_letter_records"] = 14
    src["qualified_reference_letter_records"] = 459
    path.write_text(json.dumps(src))
    assert hop_readiness_status(crosswalk_audit_path=path)["fda_identity_crosswalk"] is None
    src["qualified_reference_letter_records"] = 19
    src["identity_link_status_counts"]["NOT_IN_COHORT"] = 1
    path.write_text(json.dumps(src))
    assert hop_readiness_status(crosswalk_audit_path=path)["fda_identity_crosswalk"] is None
