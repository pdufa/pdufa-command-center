"""Safety gate: staging records cannot silently enter the HOP model."""
import json
from pathlib import Path
from app.hop_history_ingest import parse_history

STAGING = Path(__file__).resolve().parents[1] / "app" / "research_sources" / "hop_fda_outcome_staging.json"

def test_staged_cases_are_quarantined():
    raw = json.loads(STAGING.read_text(encoding="utf-8"))
    assert raw["status"] == "STAGING_ONLY_NOT_MODEL_ELIGIBLE"
    assert raw["records"]
    for record in raw["records"]:
        assert record["model_eligible"] is False
        assert record["review_status"] != "VERIFIED_COMPLETE"
        assert record["source_url"].startswith("https://www.accessdata.fda.gov/")
        assert any(record[key] is None for key in ("indication", "therapeutic_area", "modality", "phase", "evidence_as_of"))

def test_staging_not_accepted_by_training_import():
    raw = json.loads(STAGING.read_text(encoding="utf-8"))
    try:
        parse_history(json.dumps(raw["records"]))
    except ValueError:
        return
    raise AssertionError("Incomplete staging data must not enter model history")
