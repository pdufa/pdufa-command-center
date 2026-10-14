"""Navigation guard: the scoring-audit UI is gone but backend remains."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_six_pdufa_subtabs_keep_scans_and_trading():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index('if page == "PDUFA":')
    end = source.index('elif page == "2. PDUFA CALENDAR":', start)
    pdufa = source[start:end]
    assert '["GEM", "PIPELINE", "PRE PHASE 3", "POST PHASE 3", "SCANS", "WT"]' in pdufa
    assert 'nightly_report_tab, watch_trade_tab = st.tabs(' in pdufa
    assert 'with nightly_report_tab:' in pdufa
    assert 'render_nightly_scan_report()' in pdufa
    assert 'with watch_trade_tab:' in pdufa
    assert 'render_watch_trade_dashboard()' in pdufa
    assert 'with scoring_tests_tab:' not in pdufa
    assert 'render_score_input_audit()' not in pdufa
    assert (ROOT / "score_input_audit.py").is_file()
    assert (ROOT / "scripts/nightly_scoring_audit.py").is_file()


def test_operations_site_score_does_not_duplicate_pdufa_input_tab():
    site_source = (ROOT / "site_scorecard.py").read_text(encoding="utf-8")
    assert "def render_site_scorecard():" in site_source
    assert "render_operational_scorecard()" in site_source
    assert "render_score_input_audit" not in site_source
