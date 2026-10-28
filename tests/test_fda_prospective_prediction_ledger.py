import json

import pytest

from research.fda_prospective_prediction_ledger import append_prediction


BASE = dict(
    trial_id="EXAMPLE-TRIAL",
    prediction="ABSTAIN",
    cutoff_utc="2026-12-01T00:00:00Z",
    recorded_at_utc="2026-11-01T00:00:00Z",
    model_commit="abc123",
    evidence_manifest_sha256="a" * 64,
)


def test_append_and_chain(tmp_path):
    path = tmp_path / "predictions.jsonl"
    first = append_prediction(path, **BASE)
    second = append_prediction(path, **BASE)
    events = [json.loads(x) for x in path.read_text().splitlines()]
    assert len(events) == 2
    assert events[0]["entry_hash"] == first
    assert events[1]["previous_hash"] == first
    assert events[1]["entry_hash"] == second


def test_post_cutoff_rejected(tmp_path):
    with pytest.raises(ValueError, match="after cutoff"):
        append_prediction(
            tmp_path / "predictions.jsonl",
            **{**BASE, "recorded_at_utc": "2026-12-02T00:00:00Z"},
        )


def test_tampered_ledger_rejected(tmp_path):
    path = tmp_path / "predictions.jsonl"
    append_prediction(path, **BASE)
    text = path.read_text().replace('"ABSTAIN"', '"PASS"')
    path.write_text(text)
    with pytest.raises(ValueError, match="Modified ledger"):
        append_prediction(path, **BASE)
