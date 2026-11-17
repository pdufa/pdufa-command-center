import json
from pathlib import Path

from assessment_levels_07_20.historical_discovery_gate import inspect_discovery_records


def test_keynote522_discovery_seed_is_quarantined():
    path = Path(__file__).resolve().parents[3] / "docs/data/keynote522_discovery_only.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = inspect_discovery_records(payload)
    assert result["discovery_record_valid"], result["errors"]
    assert result["event_count"] == 1
    assert result["outcome_quarantined_count"] == 1
    assert result["blind_eligible"] is False
    assert result["accuracy_evaluated"] is False


def test_rejects_unquarantined_outcome():
    payload = {"status": "DISCOVERY_ONLY", "blind_eligible": False,
               "source_bytes_verified": False, "events": [
                   {"nct_id": "NCT03036488", "application_id": "BLA125514/S-089",
                    "indication": "TNBC", "sources": [
                        {"outcome_exposing": True, "verified_historical_bytes": False}]}]}
    result = inspect_discovery_records(payload)
    assert not result["discovery_record_valid"]
    assert any("OUTCOME_NOT_QUARANTINED" in error for error in result["errors"])


def test_rejects_claimed_blind_eligibility():
    payload = {"status": "DISCOVERY_ONLY", "blind_eligible": True,
               "source_bytes_verified": False, "events": [
                   {"nct_id": "NCT03036488", "application_id": "BLA125514/S-089",
                    "indication": "TNBC", "sources": []}]}
    assert not inspect_discovery_records(payload)["discovery_record_valid"]
