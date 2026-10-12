"""Static navigation regression for the PDUFA scoring audit page."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_scoring_tests_is_last_pdufa_subtab():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    start = source.index('if page == "PDUFA":')
    end = source.index('elif page == "DISEASE & MARKET HORIZON":', start)
    pdufa = source[start:end]
    tabs = pdufa.index('["UNIFIED OVERVIEW", "PIPELINE", "PRE PHASE 3", "POST PHASE 3", "NIGHTLY SCAN REPORT", "WATCHLIST / TRADING", "SCORING TESTS"]')
    assert tabs >= 0
    assert "watch_trade_tab, scoring_tests_tab = st.tabs(" in pdufa
    assert pdufa.index("with watch_trade_tab:") < pdufa.index("with scoring_tests_tab:")
    assert "if scoring_tests_tab.open:" in pdufa
    assert "render_score_input_audit()" in pdufa


def test_operations_site_score_does_not_duplicate_pdufa_input_tab():
    site_source = (ROOT / "site_scorecard.py").read_text(encoding="utf-8")
    assert "def render_site_scorecard():" in site_source
    assert "render_operational_scorecard()" in site_source
    assert "render_score_input_audit" not in site_source
