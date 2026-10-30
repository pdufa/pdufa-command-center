import json
import pytest
from app.prediction_events import field_events, sse_lines


def test_incremental_leaf_order_and_abstain():
    events = list(field_events("NCT01234567", {"nct_id": "NCT01234567", "sponsor": {"name": "Example"}}))
    assert [e["type"] for e in events[:6]] == ["started", "leaf", "leaf", "leaf", "leaf", "progress"]
    assert events[-1]["type"] == "complete"
    assert [e["section"] for e in events if e["type"] == "progress"] == ["trial_identity", "trial_design", "clinical_results", "regulatory"]
    assert events[1]["status"] == "AVAILABLE"
    assert events[2]["status"] == "UNAVAILABLE"
    assert events[5]["available"] == 1
    assert events[5]["total"] == 4
    assert events[-1]["decision"] == "ABSTAIN"
    assert not any(e.get("spinner") for e in events)


def test_sse_format_and_identity():
    stream = "".join(sse_lines("NCT01234567", {"nct_id": "NCT01234567"}))
    assert "event: started\n" in stream
    assert "event: complete\n" in stream
    assert len([x for x in stream.splitlines() if x.startswith("data: ")]) == 21
    with pytest.raises(ValueError):
        list(field_events("NCT01234567", {"nct_id": "NCT87654321"}))
