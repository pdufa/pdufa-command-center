from research.predictions_trial_source import build_prediction_candidates


def test_merge_verified_sources():
    rows = build_prediction_candidates(
        phase3_released=[
            {"trial_id": "NCT001", "label": "Trial A", "phase3_data_released": True, "source_url": "https://clinicaltrials.gov/study/NCT001"},
            {"trial_id": "NCT002", "phase3_data_released": False, "source_url": "https://example.org/no"},
        ],
        gem_jr=[{"trial_id": "NCT001", "label": "Trial A", "source_url": "https://example.org/gemjr"}],
        gem=[{"trial_id": "NCT001", "source_url": "https://example.org/gem"}],
        wt=[{"trial_id": "NCT003", "source_url": "https://example.org/wt"}],
    )
    assert len(rows) == 2
    assert rows[0]["groups"] == ["GEM", "GEM_JR", "PHASE3_DATA_RELEASED"]
    assert len(rows[0]["source_urls"]) == 3
    assert rows[1]["groups"] == ["WT"]


def test_unverifiable_rows_not_shown():
    assert build_prediction_candidates(gem=[{"trial_id": "NCT1"}]) == []
