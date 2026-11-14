"""Guard active Next.js navigation after retiring Streamlit/GEM stage UI.

Historical GEM/score-input research code may remain in archives, but the live
top navigation must not link to it. Nightly read-only input audits remain.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "new-platform/frontend/app"


def test_active_navigation_links_only_supported_primary_destinations():
    source = (APP / "GlobalNavigation.tsx").read_text(encoding="utf-8")
    expected = {
        "PAST": "/past",
        "POOL": "/pool",
        "INDICATIONS": "/indications",
        "FOCUS": "/focus",
        "WT": "/wt",
        "CAL": "/cal",
        "COMPANY": "/company",
        "NEWS": "/news",
        "PREDICTIONS": "/predictions",
        "ASSESMENTS": "/predictions/assessment",
        "TOOLS": "/tools",
        "INSTALLATION": "/installation-audit",
    }
    for label, href in expected.items():
        assert f'label:"{label}",href:"{href}"' in source
        assert (APP / href.lstrip("/") / "page.tsx").is_file(), href
    live_links = re.findall(r'label:"([^"]+)",href:"([^"]+)"', source)
    assert len(live_links) == len(expected)
    assert list(dict(live_links))[-2:] == ["TOOLS", "INSTALLATION"]
    assert all(label not in {"GEM", "GEM JR", "GEM_JR", "TOP", "BOTTOM", "PIPELINE"} for label, _ in live_links)
    assert 'aria-label="Site navigation"' in source
    # Research source history remains in Git; legacy clinical cohorts are not
    # active menu choices. POOL and FOCUS remain the only candidate populations;
    # WT is a trading-research view, not an additional candidate population.
    # PREDICTIONS is a read-only FDA outcome-status destination.
    # INSTALLATION is a read-only audit, not an extra trial cohort or scoring tier.

def test_retired_scoring_ui_is_absent_but_nightly_input_audits_are_preserved():
    nav = (APP / "GlobalNavigation.tsx").read_text(encoding="utf-8")
    assert "scoring_tests_tab" not in nav
    assert "render_score_input_audit()" not in nav
    assert (ROOT / "score_input_audit.py").is_file()
    assert (ROOT / "scripts/nightly_scoring_audit.py").is_file()


def test_operations_site_score_does_not_duplicate_pdufa_input_tab():
    site_source = (ROOT / "site_scorecard.py").read_text(encoding="utf-8")
    assert "def render_site_scorecard():" in site_source
    assert "render_operational_scorecard()" in site_source
    assert "render_score_input_audit" not in site_source
