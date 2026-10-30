import json
import pytest

from research.predictions_source_loader import load_trial_snapshot


def test_snapshot_combines_four_sources(tmp_path):
    path = tmp_path / "trials.json"
    path.write_text(json.dumps({
        "phase3_released": [{"trial_id": "NCT100", "phase3_data_released": True, "source_url": "https://clinicaltrials.gov/study/NCT100"}],
        "gem_jr": [{"trial_id": "NCT100", "source_url": "https://example.org/jr"}],
        "gem": [],
        "wt": [{"trial_id": "NCT200", "source_url": "https://example.org/wt"}],
    }))
    rows = load_trial_snapshot(path)
    assert len(rows) == 2
    assert rows[0]["groups"] == ["GEM_JR", "PHASE3_DATA_RELEASED"]


def test_bad_feed_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"gem": {"trial_id": "NCT100"}}')
    with pytest.raises(ValueError, match="Invalid trial feed"):
        load_trial_snapshot(path)
