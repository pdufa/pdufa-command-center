import json
import pytest
from app.hop_history_ingest import parse_history

def example():
    return dict(case_id="fda-example-1", indication="lung cancer",
                therapeutic_area="oncology", modality="antibody", phase=3,
                decision_date="2020-01-02", outcome="APPROVED",
                evidence_as_of="2020-01-02",
                source_url="https://www.fda.gov/drugs")

def test_empty_inventory_is_explicit():
    assert parse_history("[]") == []

def test_valid_curated_record():
    assert parse_history(json.dumps([example()]))[0].case_id == "fda-example-1"

@pytest.mark.parametrize("field,value", [
    ("source_url", "https://example.com/fda"),
    ("outcome", "PENDING"),
    ("phase", 2),
    ("decision_date", "2099-01-01"),
    ("case_id", ""),
])
def test_rejects_invalid_evidence(field, value):
    row = example()
    row[field] = value
    with pytest.raises(ValueError):
        parse_history(json.dumps([row]))

def test_duplicate_case_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        parse_history(json.dumps([example(), example()]))
