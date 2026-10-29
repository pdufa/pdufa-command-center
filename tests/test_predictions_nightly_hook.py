from research.predictions_nightly_hook import after_nightly_scan


def test_nightly_hook_disabled_by_default(tmp_path):
    called = []
    def provider(trial_id):
        called.append(trial_id)
        return {}
    result = after_nightly_scan(
        tmp_path, [{"trial_id": "T1", "groups": ["WT"]}], provider,
    )
    assert result["status"] == "DISABLED"
    assert called == []
    assert list(tmp_path.iterdir()) == []


def test_explicit_nightly_hook_runs_sourced_checklist(tmp_path):
    result = after_nightly_scan(
        tmp_path,
        [{"trial_id": "T1", "groups": ["GEM_JR", "WT"]}],
        lambda _: {},
        enabled=True,
    )
    assert result["status"] == "FINISHED"
    assert len(result["schedule"]["queued"]) == 1
    assert len(result["worker"]["processed"]) == 1
    assert result["worker"]["processed"][0]["decision"] == "ABSTAIN"
