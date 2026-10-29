import pytest
from research.workspace_pipeline_adapter import adapt_workspace_candidates


def _workspace():
    return {"sourceHealth": {"state": "OK", "pipelineSourceParity": {"exactPrograms": 1}},
            "pipeline": [{"id": "program-1", "ticker": "ABC",
                          "marketCap": 500000000, "capSource": "dated-source",
                          "capChecked": "2026-10-29"}]}


def test_actual_workspace_schema_still_abstains_without_restrictions():
    result = adapt_workspace_candidates(_workspace())
    assert result["total"] == 1
    assert result["records"][0]["scope"] == "BLOCKED"
    assert "PIPELINE_RESTRICTIONS_NOT_CONFIRMED" in result["records"][0]["blockers"]
    assert result["prediction_status"] == "ABSTAIN"


def test_parity_mismatch_fails_closed():
    value = _workspace()
    value["sourceHealth"]["pipelineSourceParity"]["exactPrograms"] = 2
    with pytest.raises(ValueError):
        adapt_workspace_candidates(value)


def test_stale_source_fails_closed():
    value = _workspace()
    value["sourceHealth"]["state"] = "STALE"
    with pytest.raises(ValueError):
        adapt_workspace_candidates(value)
