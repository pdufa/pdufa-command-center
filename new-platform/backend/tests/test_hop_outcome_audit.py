"""All records in these offline HOP audit tests are fictitious."""
import csv
from datetime import date

import pytest

from app.hop_outcome_audit import GATES_NOT_MET, audit_quarantined_outcome_intake
from app.hop_outcomes_import import REQUIRED_COLUMNS, validate_csv

AS_OF = date(2026, 10, 25)


def example(case_id="SYNTHETIC-001", application="NDA000001", outcome="APPROVED"):
    return {
        "case_id": case_id,
        "application_id": application,
        "review_cycle": "1",
        "drug_name": "Fictitious drug",
        "sponsor": "Fictitious sponsor",
        "indication": "Test-only condition",
        "therapeutic_area": "synthetic",
        "modality": "small molecule",
        "phase": "3",
        "decision_date": "2020-01-01",
        "outcome": outcome,
        "public_features_as_of": "2019-12-30",
        "evidence_as_of": "2020-01-02",
        "source_url": "https://www.fda.gov/example",
        "source_title": "Synthetic title (not a verified source)",
    }


def write_fixture(tmp_path, rows):
    path = tmp_path / "synthetic.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def report(tmp_path, rows):
    return audit_quarantined_outcome_intake(
        validate_csv(write_fixture(tmp_path, rows), as_of=AS_OF)
    )


def test_empty_template_stays_quarantined_without_prediction(tmp_path):
    result = report(tmp_path, [])
    assert result["intake_status"] == "REVIEW_REQUIRED"
    assert result["staged_csv_rows"] == 0
    assert result["prediction_probability"] is None
    assert result["approval_rate"] is None
    assert result["model_eligible_records"] == 0
    assert len(result["unmet_release_gates"]) == len(GATES_NOT_MET)


def test_mixed_unverified_labels_are_not_an_approval_rate(tmp_path):
    result = report(tmp_path, [
        example(),
        example("SYNTHETIC-002", "BLA000002", "COMPLETE_RESPONSE"),
        example("SYNTHETIC-003", "ANDA000003", "WITHDRAWN"),
    ])
    assert result["intake_status"] == "SCHEMA_VALIDATED_REVIEW_REQUIRED"
    assert result["staged_csv_rows"] == 3
    assert result["unverified_outcome_claims_by_type"] == {
        "APPROVED": 1, "COMPLETE_RESPONSE": 1, "OTHER_NONAPPROVAL": 0, "WITHDRAWN": 1,
    }
    assert result["unverified_application_claims_by_type"] == {
        "NDA": 1, "BLA": 1, "ANDA": 1,
    }
    assert result["unverified_decision_year_claims"] == {"2020": 3}
    assert result["complete_decision_denominator_verified"] is False
    assert result["model_validated"] is False
    assert result["prediction_available"] is False
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None


def test_partial_invalid_intake_reports_reasons_not_a_cohort(tmp_path):
    invalid = example("SYNTHETIC-002", "BLA000002", "COMPLETE_RESPONSE")
    invalid["public_features_as_of"] = "2020-01-01"
    result = report(tmp_path, [example(), invalid])
    assert result["intake_status"] == "REVIEW_REQUIRED"
    assert result["staged_csv_rows"] == 1
    assert result["rejected_csv_rows"] == 1
    assert result["rejected_rows_by_reason"] == {"features_not_predecision": 1}
    assert result["model_eligible_records"] == 0


def test_duplicate_application_cycle_never_qualifies(tmp_path):
    result = report(tmp_path, [
        example(),
        example("SYNTHETIC-002", "NDA-000001"),
    ])
    assert result["staged_csv_rows"] == 0
    assert result["rejected_csv_rows"] == 2
    assert result["rejected_rows_by_reason"] == {
        "duplicate_application_review_cycle": 2
    }
    assert result["prediction_probability"] is None


@pytest.mark.parametrize("field,value", [
    ("model_eligible_records", 1),
    ("independently_verified", True),
    ("probability", 0.7),
    ("accepted", 1000),
    ("status", "MODEL_READY"),
])
def test_any_claim_of_training_or_inconsistent_counts_fails_closed(
    tmp_path, field, value
):
    original = validate_csv(write_fixture(tmp_path, [example()]), as_of=AS_OF)
    original[field] = value
    with pytest.raises(ValueError):
        audit_quarantined_outcome_intake(original)
