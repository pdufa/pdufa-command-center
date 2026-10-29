from research.predictions_background_scheduler import schedule_eligible_predictions


def test_disabled_by_default(tmp_path):
    rows = [{"trial_id": "T1", "groups": ["WT"]}]
    result = schedule_eligible_predictions(tmp_path, rows)
    assert result["status"] == "DISABLED"
    assert list(tmp_path.iterdir()) == []


def test_queues_once_and_deduplicates(tmp_path):
    rows = [
        {"trial_id": "T1", "groups": ["GEM_JR"]},
        {"trial_id": "T1", "groups": ["WT"]},
        {"trial_id": "T2", "groups": ["GEM"]},
    ]
    result = schedule_eligible_predictions(tmp_path, rows, enabled=True)
    assert len(result["queued"]) == 2
    again = schedule_eligible_predictions(tmp_path, rows, enabled=True)
    assert again["status"] == "NO_NEW_JOBS"
    assert len(again["skipped"]) == 2


def test_batch_limit(tmp_path):
    rows = [{"trial_id": f"T{i}", "groups": ["WT"]} for i in range(3)]
    result = schedule_eligible_predictions(tmp_path, rows, enabled=True, max_new_jobs=1)
    assert len(result["queued"]) == 1
    assert len(result["skipped"]) == 2
