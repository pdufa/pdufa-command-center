"""Regression tests for the original Streamlit Pipeline universe, not scanner output."""
from datetime import date

from app.pipeline_universe_rules import original_pipeline_universe


TODAY = date(2026, 10, 16)


def test_overlapping_nct_records_merge_without_disappearing():
    """The old adapter deleted every NCT appearing in both clinical feeds."""
    files = {
        "phase_pipeline.csv": [
            {"nct_id": "NCT00000001", "ticker": "AAA", "company": "A",
             "phases": "PHASE2|PHASE3", "status": "RECRUITING",
             "drug": "Drug A", "source_url": "https://clinicaltrials.gov/study/NCT00000001",
             "checked_at": "2026-10-15"},
            {"nct_id": "NCT00000002", "ticker": "BBB",
             "phases": "PHASE3", "checked_at": "2026-10-15"},
        ],
        "all_phase_trials.csv": [
            {"nct_id": "NCT00000001", "ticker": "AAA", "company": "A",
             "phase": "PHASE3", "status": "COMPLETED", "results_posted": "2026-09-15",
             "source_url": "https://clinicaltrials.gov/study/NCT00000001",
             "checked_at": "2026-10-16"},
            {"nct_id": "NCT00000003", "ticker": "CCC", "phase": "PHASE1",
             "checked_at": "2026-10-16"},
        ],
    }
    universe = original_pipeline_universe(files, TODAY)
    assert set(universe) == {
        "TRIAL|NCT00000001", "TRIAL|NCT00000002", "TRIAL|NCT00000003"
    }
    assert universe["TRIAL|NCT00000001"]["stage"] == "Phase 3 Results"
    assert universe["TRIAL|NCT00000001"]["drug"] == "Drug A"
    assert universe["TRIAL|NCT00000001"]["status"] == "COMPLETED"


def test_source_announcements_enrich_existing_nct_and_keep_no_nct_results():
    files = {
        "all_phase_trials.csv": [
            {"nct_id": "NCT00000004", "ticker": "AAA", "phase": "PHASE3",
             "source_url": "https://clinicaltrials.gov/study/NCT00000004"},
        ],
        "phase3_announcements.csv": [
            {"nct_id": "NCT00000004", "ticker": "AAA",
             "phase3_results_posted_at": "2026-10-08",
             "phase3_results_source": "https://example.org/verified-trial"},
            {"nct_id": "", "ticker": "BBB", "drug": "Drug B",
             "phase3_results_posted_at": "2026-10-09",
             "phase3_results_source": "https://example.org/verified-company"},
        ],
    }
    rows = original_pipeline_universe(files, TODAY)
    assert len(rows) == 2
    assert rows["TRIAL|NCT00000004"]["stage"] == "Phase 3 Results"
    result = next(v for k,v in rows.items() if k.startswith("RESULT|"))
    assert result["stage"] == "Phase 3 Results"
    assert result["recordType"] == "Result announcement"


def test_regulatory_exact_events_are_not_joined_by_ticker():
    files = {
        "prediction_engine_history.csv": [
            {"ticker": "AAA", "event_key": "AAA|2026-12-09|Drug A",
             "drug": "Drug A", "pdufa_date": "2026-12-09"},
        ],
        "pdufa_candidates.csv": [
            {"ticker": "AAA", "event_key": "AAA|2026-12-09|Drug A",
             "drug": "Drug A", "fda_acceptance_date": "2026-10-01"},
            {"ticker": "AAA", "event_key": "AAA|2026-11-21|Drug B",
             "drug": "Drug B", "pdufa_date": "2026-11-21"},
        ],
    }
    rows = original_pipeline_universe(files, TODAY)
    assert len(rows) == 2
    assert rows["APPLICATION|AAA|2026-12-09|Drug A"]["stage"] == "PDUFA Decision"
    assert rows["APPLICATION|AAA|2026-11-21|Drug B"]["stage"] == "PDUFA Decision"


def test_every_exact_program_has_one_current_stage():
    files = {
        "all_phase_trials.csv": [
            {"nct_id": f"NCT{n:08d}", "ticker": "AAA",
             "phase": "PHASE3" if n%2 else "PHASE2"}
            for n in range(1,11)
        ],
    }
    records=original_pipeline_universe(files,TODAY)
    assert len(records)==10
    assert sum(v["stage"] == "Phase 3" for v in records.values()) == 5
    assert sum(v["stage"] == "Phase 2" for v in records.values()) == 5
    assert len({v["id"] for v in records.values()}) == 10
