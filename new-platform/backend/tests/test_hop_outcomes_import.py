"""CSV intake checks only; all examples below are fictitious test fixtures."""
import csv
from datetime import date

import pytest

from app.hop_outcomes_import import (
    REQUIRED_COLUMNS, normalize_application_id, validate_csv, validate_record,
)

AS_OF = date(2026, 10, 25)


def valid_row():
    return {
        "case_id": "SYNTHETIC-FDA-001",
        "application_id": "NDA-000001",
        "review_cycle": "1",
        "drug_name": "Fictitious drug",
        "sponsor": "Fictitious sponsor",
        "indication": "Example indication",
        "therapeutic_area": "oncology",
        "modality": "antibody",
        "phase": "3",
        "decision_date": "2020-01-01",
        "outcome": "APPROVED",
        "public_features_as_of": "2019-12-30",
        "evidence_as_of": "2020-01-02",
        "source_url": "https://www.fda.gov/example",
        "source_title": "Fictitious source title",
    }


def test_accepts_schema_complete_example_but_never_adjudicates():
    record, errors = validate_record(valid_row(), as_of=AS_OF)
    assert not errors
    assert record.outcome == "APPROVED"
    assert record.application_id == "NDA000001"
    assert record.public_features_as_of < record.decision_date
    assert record.evidence_as_of >= record.decision_date


def test_rejects_decision_after_import_cutoff():
    row = valid_row()
    row["decision_date"] = "2027-01-01"
    assert "decision_after_import_as_of" in validate_record(row, as_of=AS_OF)[1]


def test_rejects_outcome_evidence_that_predates_decision():
    row = valid_row()
    row["evidence_as_of"] = "2019-12-31"
    assert "outcome_evidence_predates_decision" in validate_record(row, as_of=AS_OF)[1]


def test_rejects_postdecision_features_even_if_outcome_source_valid():
    row = valid_row()
    row["public_features_as_of"] = "2020-01-01"
    assert "features_not_predecision" in validate_record(row, as_of=AS_OF)[1]


def test_rejects_non_fda_and_spoofed_domains():
    for url in (
        "https://example.com/example",
        "https://www.fda.gov.evil.example/letter",
        "https://www.fda.gov@evil.example/letter",
        "http://www.fda.gov/example",
        "https://www.fda.gov:8443/example",
        "https://www.fda.gov/example#fake",
    ):
        row = valid_row()
        row["source_url"] = url
        assert "source_not_official_fda_https" in validate_record(row, as_of=AS_OF)[1]


def test_rejects_malformed_application_and_cycle():
    row = valid_row()
    row["application_id"] = "foobar"
    assert "invalid_application_id" in validate_record(row, as_of=AS_OF)[1]
    row = valid_row()
    row["review_cycle"] = "0"
    assert "invalid_date_phase_or_review_cycle" in validate_record(row, as_of=AS_OF)[1]


def save_csv(path, rows, headers=REQUIRED_COLUMNS):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_csv_schema_good_is_still_quarantined(tmp_path):
    path = tmp_path / "outcomes.csv"
    save_csv(path, [valid_row()])
    result = validate_csv(path, as_of=AS_OF)
    assert result["status"] == "SCHEMA_VALIDATED_REVIEW_REQUIRED"
    assert result["accepted"] == 1
    assert result["independently_verified"] is False
    assert result["model_eligible_records"] == 0
    assert result["probability"] is None


def test_duplicate_application_cycle_rejected_even_with_different_case_ids(tmp_path):
    path = tmp_path / "outcomes.csv"
    row = valid_row()
    other = dict(row, case_id="SYNTHETIC-FDA-002", application_id="NDA000001")
    save_csv(path, [row, other])
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0
    assert result["rejected"] == 2
    assert all("duplicate_application_review_cycle" in x["errors"] for x in result["rejections"])


def test_missing_or_unknown_header_fails_closed(tmp_path):
    path = tmp_path / "outcomes.csv"
    save_csv(path, [], headers=REQUIRED_COLUMNS[:-1])
    result = validate_csv(path, as_of=AS_OF)
    assert result["status"] == "REJECTED_SCHEMA"
    assert result["model_eligible_records"] == 0


def test_csv_extra_fields_do_not_hide_a_duplicate_identity_claim(tmp_path):
    path = tmp_path / "outcomes.csv"
    save_csv(path, [valid_row()])
    with path.open("a", encoding="utf-8") as file:
        file.write(",".join(valid_row()[key] for key in REQUIRED_COLUMNS) + ",EXTRA\n")
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0
    assert result["rejected"] == 2
    assert [r["line"] for r in result["rejections"]] == [2, 3]
    assert all("duplicate_application_review_cycle" in r["errors"] for r in result["rejections"])
    assert "extra_csv_fields" in result["rejections"][1]["errors"]


def test_required_columns_include_distinct_temporal_fields():
    assert {"application_id", "review_cycle", "source_url", "public_features_as_of", "evidence_as_of"}.issubset(REQUIRED_COLUMNS)


@pytest.mark.parametrize("invalid", [
    {"source_url": "https://example.com/not-fda"},
    {"decision_date": "not-a-date"},
    {"drug_name": ""},
    {"public_features_as_of": "2020-01-02"},
    {"outcome": "UNSUPPORTED"},
])
@pytest.mark.parametrize("reverse", [False, True])
def test_invalid_claim_cannot_leave_its_duplicate_cycle_accepted(tmp_path, invalid, reverse):
    good = valid_row()
    other = dict(good, case_id="SYNTHETIC-FDA-002", outcome="COMPLETE_RESPONSE")
    other.update(invalid)
    rows = [good, other]
    if reverse:
        rows.reverse()
    path = tmp_path / "conflicting.csv"
    save_csv(path, rows)
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0 and result["rejected"] == 2
    assert result["records"] == []
    assert [r["line"] for r in result["rejections"]] == [2, 3]
    assert all("duplicate_application_review_cycle" in r["errors"] for r in result["rejections"])
    invalid_rejection = next(r for r in result["rejections"] if r["case_id"] == other["case_id"])
    assert len(invalid_rejection["errors"]) >= 2
    assert result["model_eligible_records"] == 0
    assert result["independently_verified"] is False and result["probability"] is None


@pytest.mark.parametrize("reverse", [False, True])
def test_duplicate_case_id_is_reconciled_even_when_cycle_differs_and_row_is_invalid(tmp_path, reverse):
    first = valid_row()
    other = dict(first, case_id="  SYNTHETIC-FDA-001  ", application_id="BLA000002",
                 source_url="https://example.com/not-fda")
    rows = [first, other]
    if reverse:
        rows.reverse()
    path = tmp_path / "case-id.csv"
    save_csv(path, rows)
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0 and result["rejected"] == 2
    assert all("duplicate_case_id" in r["errors"] for r in result["rejections"])
    assert all("duplicate_application_review_cycle" not in r["errors"] for r in result["rejections"])
    assert {r["line"] for r in result["rejections"]} == {2, 3}


def test_nonempty_case_id_is_reconciled_even_if_the_second_cycle_identity_is_unparseable(tmp_path):
    first = valid_row()
    other = dict(first, application_id="not-an-application", review_cycle="not-a-cycle")
    path = tmp_path / "unparseable-cycle.csv"
    save_csv(path, [first, other])
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0 and result["rejected"] == 2
    assert all("duplicate_case_id" in r["errors"] for r in result["rejections"])
    assert all("duplicate_application_review_cycle" not in r["errors"] for r in result["rejections"])


@pytest.mark.parametrize("prefix", ["NDA", "BLA", "ANDA"])
def test_duplicate_identity_normalization_matches_record_validation(tmp_path, prefix):
    first = dict(valid_row(), application_id=f"{prefix}000001")
    other = dict(first, case_id="SYNTHETIC-FDA-002", application_id=f"  {prefix.lower()}-000001  ",
                 review_cycle=" 1 ")
    record, errors = validate_record(other, as_of=AS_OF)
    assert not errors and record.application_id == f"{prefix}000001"
    assert normalize_application_id(other["application_id"]) == record.application_id
    path = tmp_path / "aliases.csv"
    save_csv(path, [first, other])
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == 0 and result["rejected"] == 2
    assert all("duplicate_application_review_cycle" in r["errors"] for r in result["rejections"])


@pytest.mark.parametrize("changes", [
    {"application_id": "NDA--000001"},
    {"application_id": "NDA000001junk"},
    {"application_id": "NDA 000001"},
    {"review_cycle": "01"},
    {"review_cycle": "0"},
    {"review_cycle": "1.0"},
])
def test_malformed_cycle_identity_does_not_poison_valid_distinct_case(tmp_path, changes):
    first = valid_row()
    other = dict(first, case_id="SYNTHETIC-FDA-002", **changes)
    path = tmp_path / "malformed.csv"
    save_csv(path, [first, other])
    result = validate_csv(path, as_of=AS_OF)
    assert result["accepted"] == result["rejected"] == 1
    assert result["records"][0].case_id == first["case_id"]
    assert result["rejections"][0]["line"] == 3
    assert all(not reason.startswith("duplicate_") for reason in result["rejections"][0]["errors"])


@pytest.mark.parametrize("value", [None, 1, True, "", "NDA--000001", "NDA000001x"])
def test_application_normalizer_does_not_infer_invalid_identities(value):
    assert normalize_application_id(value) is None


def test_duplicate_reconciliation_is_order_invariant_with_one_rejection_per_row(tmp_path):
    good = valid_row()
    other = dict(good, case_id="SYNTHETIC-FDA-002", outcome="COMPLETE_RESPONSE",
                 source_url="https://example.com/not-fda")
    results = []
    for rows in ([good, other], [other, good]):
        path = tmp_path / "order.csv"
        save_csv(path, rows)
        result = validate_csv(path, as_of=AS_OF)
        assert result["accepted"] == 0 and result["rejected"] == 2
        assert len({r["line"] for r in result["rejections"]}) == 2
        results.append({r["case_id"]: sorted(r["errors"]) for r in result["rejections"]})
    assert results[0] == results[1]
