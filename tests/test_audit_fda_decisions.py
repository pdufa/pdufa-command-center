"""Staging audit regressions with synthetic source observations only."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_fda_decisions import audit, load_rows


def row(**changes):
    return {"application_id": "BLA125807", "submission_id": "ORIG-000", "review_cycle": 1,
            "action": "crl", "decision_date": "2024-04-16", "evidence_as_of": "2024-04-17",
            "retrieved_on": "2024-04-18", "source_url": "https://www.fda.gov/test-fixture", **changes}


def test_staging_counts_distinct_from_verified_counts():
    result = audit([row(), row(), row(action="approval", review_cycle=2, decision_date="2025-04-28",
                    evidence_as_of="2025-04-29", retrieved_on="2025-04-30")], as_of="2026-10-27")
    assert result["input_events"] == 3
    assert result["application_counts"]["candidate_review_cycles"] == 2
    assert result["independently_verified_pass_count"] == result["independently_verified_fail_count"] == 0
    assert result["model_eligible_records"] == 0
    assert result["source_content_verified"] is False
    assert result["complete_application_denominator_verified"] is False


def test_documented_action_without_cycle_and_publication_is_not_promoted():
    result = audit([row(review_cycle=None, evidence_as_of=None)], as_of="2026-10-27")
    assert result["application_counts"]["candidate_review_cycles"] == 0
    assert set(result["excluded_observations"][0]["issues"]) == {
        "missing_exact_application_submission_cycle", "unknown_or_invalid_source_chronology"}


def test_empty_inventory_has_zero_verified_counts_not_accuracy():
    result = audit([], as_of="2026-10-27")
    assert result["input_events"] == 0
    assert result["prediction_model_validated"] is False
    assert result["independent_backtest_complete"] is False


def test_csv_and_jsonl_intake_agree(tmp_path):
    import csv
    source = row()
    csv_path = tmp_path / "source.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(source))
        writer.writeheader()
        writer.writerow(source)
    json_path = tmp_path / "source.jsonl"
    json_path.write_text(json.dumps(source) + "\n")
    assert audit(load_rows(csv_path), as_of="2026-10-27") == audit(load_rows(json_path), as_of="2026-10-27")


def test_nonobject_jsonl_rejected(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text("[]\n")
    with pytest.raises(ValueError, match="expected JSON object"):
        list(load_rows(path))


def test_empty_inventory_still_validates_cutoff():
    with pytest.raises(ValueError, match="as_of"):
        audit([], as_of="20261027")
