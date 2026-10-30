import pytest
from research.preliminary_pipeline_batch import triage_pipeline_export


def test_batch_triage_preserves_input_and_counts():
    rows = [
        {"program_id": "A", "publicly_traded": True, "market_cap_usd": 300000000,
         "pipeline_member": True, "fda_pdufa_target_confirmed": True},
        {"program_id": "B", "publicly_traded": True, "market_cap_usd": 299999999,
         "pipeline_member": True, "fda_pdufa_target_confirmed": True},
    ]
    before = [dict(row) for row in rows]
    result = triage_pipeline_export(rows)
    assert rows == before
    assert result["total"] == 2
    assert result["candidate_for_evidence_review"] == 1
    assert result["blocked"] == 1
    assert all(row["prediction"] is None for row in result["records"])
    assert result["prediction_status"] == "ABSTAIN"
    assert result["data_authenticity_verified"] is False


@pytest.mark.parametrize("rows", [None, {}, [None], [{"program_id": ""}],
                                  [{"program_id": "A"}, {"program_id": "A"}]])
def test_invalid_batch_fails_closed(rows):
    with pytest.raises(ValueError):
        triage_pipeline_export(rows)


def test_empty_export_is_not_a_prediction():
    result = triage_pipeline_export([])
    assert result["total"] == 0
    assert result["prediction_status"] == "ABSTAIN"
