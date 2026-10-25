"""Navigation guard: the scoring-audit UI is gone but backend remains.

The PDUFA operator workspace moved from removed Streamlit app.py to
new-platform/frontend/app/Workspace.tsx. Keep this test on the live UI.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_scans_is_top_level_before_results_and_pdufa_subtabs_keep_trading():
    source = (ROOT / "new-platform/frontend/app/Workspace.tsx").read_text(encoding="utf-8")

    # Test the active Next.js workspace, not the retired Streamlit module.
    for nav in ('"PIPELINE"', '"GEM_JR"', '"GEM"', '"WT"', '"TRADING"'):
        assert nav in source
    assert '["PIPELINE","PIPELINE"]' in source
    assert '["GEM_JR","GEM JR"]' in source
    assert '["GEM","GEM"]' in source
    # SCANS was intentionally moved out of the inner PDUFA tabs, before RESULTS.
    # New first-class tabs (GOAL, BACKUP, etc.) may be added over time.
    # Verify the allowed tabs without freezing the entire TypeScript union.
    top_nav = re.search(r"\btype\s+TopNav\s*=\s*([^;]+);", source)
    assert top_nav is not None
    top_sections = set(re.findall(r'"([A-Z_]+)"', top_nav.group(1)))
    assert {"SCANS", "RESULTS", "PDUFA", "GOAL", "BACKUP"} <= top_sections
    assert '["SCANS","SCANS"]' not in source
    assert '>SCANS</button>' in source and '>RESULTS</button>' in source
    assert source.index('>SCANS</button>') < source.index('>RESULTS</button>')
    assert '["WT","WT"]' in source
    assert 'nav==="PIPELINE"' in source
    assert 'nav==="GEM_JR" || nav==="GEM"' in source
    assert 'gemBlock(nav==="GEM_JR"?"GEM_JR":"GEM")' in source
    assert 'top==="SCANS" && <PublishedScansPanel />' in source
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
