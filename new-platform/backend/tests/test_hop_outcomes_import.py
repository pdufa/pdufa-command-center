from datetime import date
from app.hop_outcomes_import import validate_record, REQUIRED_COLUMNS

AS_OF = date(2026, 10, 25)

def valid_row():
    return {
        "case_id":"FDA-APP-0001", "application_id":"NDA-000001", "drug_name":"Example",
        "sponsor":"Example Sponsor", "indication":"Example indication", "therapeutic_area":"oncology",
        "modality":"antibody", "phase":"3", "decision_date":"2020-01-01", "outcome":"APPROVED",
        "evidence_as_of":"2020-01-02", "source_url":"https://www.fda.gov/example",
        "source_title":"Example FDA record"
    }

def test_accepts_complete_source_dated_record():
    record, errors = validate_record(valid_row(), as_of=AS_OF)
    assert not errors
    assert record is not None and record.outcome == "APPROVED"

def test_rejects_decision_after_import_cutoff():
    row = valid_row()
    row["decision_date"] = "2027-01-01"
    assert "decision_after_import_as_of" in validate_record(row, as_of=AS_OF)[1]

def test_rejects_missing_primary_source():
    row = valid_row()
    row["source_url"] = "not-a-url"
    assert "source_not_https" in validate_record(row, as_of=AS_OF)[1]

def test_rejects_evidence_that_predates_decision():
    row = valid_row()
    row["evidence_as_of"] = "2019-12-31"
    assert "evidence_predates_decision" in validate_record(row, as_of=AS_OF)[1]

def test_schema_columns_are_explicit():
    assert "application_id" in REQUIRED_COLUMNS and "source_url" in REQUIRED_COLUMNS
