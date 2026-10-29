from research.predictions_tab import eligible_trials, assessment_progress


def test_picker_combines_phase3_gem_jr_gem_wt_without_duplicates():
    rows = [
        {"trial_id": "T1", "label": "Alpha", "phase3_data_released": True, "groups": ["GEM_JR"]},
        {"trial_id": "T1", "label": "Alpha", "groups": ["GEM", "WT"]},
        {"trial_id": "T2", "label": "Beta", "groups": ["PIPELINE"]},
        {"trial_id": "T3", "label": "Gamma", "groups": ["WT"]},
    ]
    trials = eligible_trials(rows)
    assert [row["trial_id"] for row in trials] == ["T1", "T3"]
    assert trials[0]["groups"] == ["GEM", "GEM_JR", "PHASE3_DATA_RELEASED", "WT"]


def test_progress_counts_only_completed_assessments():
    assert assessment_progress([
        {"status": "COMPLETED"}, {"status": "RUNNING"},
        {"status": "MISSING_EVIDENCE"}, {"status": "COMPLETED"},
    ]) == (2, 4)


def test_missing_identifiers_not_listed():
    assert eligible_trials([{"groups": ["WT"]}, {"trial_id": "A", "groups": []}]) == []
