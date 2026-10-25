import json
from datetime import date
from pathlib import Path

EXAMPLES = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
            / "hop_fda_pdf_date_review_examples.json")


def test_corrected_fda_letter_does_not_promote_publication_date_to_action_date():
    source = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    assert source["status"] == "FDA_PDF_OBSERVATION_NOT_INDEPENDENT_REVIEW_CYCLE_ADJUDICATION"
    by_id = {x["application_as_published"]: x for x in source["observations"]}
    corrected = by_id["BLA 761401"]
    assert corrected["source_letter_date_as_published"] == "04/10/2026"
    assert corrected["reported_original_action_date"] == "2025-08-27"
    assert date.fromisoformat(corrected["reported_original_action_date"]) < date(2026, 4, 10)
    assert corrected["date_discrepancy_requires_review"] is True
    assert corrected["effective_action_date_independently_adjudicated"] is False
    assert corrected["review_cycle_verified"] is False
    assert corrected["model_eligible"] is False
    assert source["model_eligible_records"] == 0
    assert source["prediction_probability"] is None


def test_legacy_bl_identifier_not_inferred_into_registry():
    source = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    legacy = next(x for x in source["observations"]
                  if x["application_as_published"] == "BL 125845")
    assert legacy["effective_action_date_proposed"] is None
    assert legacy["effective_action_date_independently_adjudicated"] is False
    assert legacy["review_cycle_verified"] is False
    assert legacy["model_eligible"] is False
    assert legacy["official_pdf_url"] == (
        "https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf")
