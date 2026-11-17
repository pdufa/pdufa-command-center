"""Isolated Level 10 contract tests; no production services required."""
from assessment_levels_07_20.level10_dossier import validate_level10_dossier


def dossier():
    return {
        "nct_id": "NCT04576949",
        "indication": "Example indication",
        "disease_subtype": "Example subtype",
        "treatment_setting": "Example line of therapy",
        "source_url": "https://example.org/guideline",
        "published_on": "2026-01-01",
        "retrieved_on": "2026-01-02",
        "cutoff_on": "2026-01-03",
        "guideline_version": "2026",
        "comparator": "Example comparator",
    }


def test_valid_inventory_never_predicts_or_scores():
    result = validate_level10_dossier(dossier())
    assert result["eligible_for_owner_review"] is True
    assert result["scientific_status"] == "NOT_VERIFIED"
    assert result["fda_prediction"] == "ABSTAIN"
    assert result["scientific_score"] is None


def test_wrong_nct_rejected():
    record = dossier()
    record["nct_id"] = "NCT04576949x"
    assert "INVALID_EXACT_NCT" in validate_level10_dossier(record)["errors"]


def test_future_source_rejected():
    record = dossier()
    record["retrieved_on"] = "2026-01-04"
    assert "SOURCE_AFTER_CUTOFF_OR_RETRIEVAL" in validate_level10_dossier(record)["errors"]


def test_missing_comparator_not_fabricated():
    record = dossier()
    del record["comparator"]
    result = validate_level10_dossier(record)
    assert not result["eligible_for_owner_review"]
    assert "comparator" in result["missing_fields"]
