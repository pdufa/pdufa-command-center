"""Navigation guard: the scoring-audit UI is gone but backend remains.

The PDUFA operator workspace moved from removed Streamlit app.py to
new-platform/frontend/app/Workspace.tsx. Keep this test on the live UI.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_consolidated_pdufa_subtabs_keep_scans_and_trading():
    source = (ROOT / "new-platform/frontend/app/Workspace.tsx").read_text(encoding="utf-8")

    # Test the active Next.js workspace, not the retired Streamlit module.
    for nav in ('"PIPELINE"', '"GEM_JR"', '"GEM"', '"SCANS"', '"WT"'):
        assert nav in source
    assert '["PIPELINE","PIPELINE"]' in source
    assert '["GEM_JR","GEM JR"]' in source
    assert '["GEM","GEM"]' in source
    assert '["SCANS","SCANS"]' in source
    assert '["WT","WT"]' in source
    assert 'nav==="PIPELINE"' in source
    assert 'nav==="GEM_JR" || nav==="GEM"' in source
    assert 'gemBlock(nav==="GEM_JR"?"GEM_JR":"GEM")' in source
    assert 'nav==="SCANS" && <PublishedScansPanel />' in source
    assert 'nav==="WT"' in source

    # Retired scoring UI must stay removed; nightly input audits still run.
    assert 'scoring_tests_tab' not in source
    assert 'render_score_input_audit()' not in source
    assert (ROOT / "score_input_audit.py").is_file()
    assert (ROOT / "scripts/nightly_scoring_audit.py").is_file()


def test_operations_site_score_does_not_duplicate_pdufa_input_tab():
    site_source = (ROOT / "site_scorecard.py").read_text(encoding="utf-8")
    assert "def render_site_scorecard():" in site_source
    assert "render_operational_scorecard()" in site_source
    assert "render_score_input_audit" not in site_source
