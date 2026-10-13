"""Regression tests for the three source-gated GEMS scans in SCANS."""
from pathlib import Path
from unittest.mock import patch

from gem_scans import STAGES, WEIGHTS, build_gem_scans

ROOT = Path(__file__).resolve().parents[1]


def sample(ticker="AAA", market=10, second=True, days=40):
    return {
        "Ticker": ticker, "Drug": "Drug " + ticker, "NCT ID": "NCT01234567",
        "Exact event": ticker + "|DRUG_20261130", "Source lane": "SAVED REGULATORY PIPELINE",
        "Entry qualification": "GREEN — GATES ATTESTED",
        "Phase 3 evidence": "VERIFIED SUCCESS — SOURCE LINKED",
        "2nd Financing Completed": (
            "YES — VERIFIED (HISTORICAL)" if second else "NOT VERIFIED"
        ),
        "PDUFA verification": "VERIFIED — SOURCE LINKED",
        "Days to PDUFA": days, "Evidence score /100": 85,
        "Clinical evidence /30": 30, "Financing evidence /20": 20,
        "Trading setup /20": 20, "PDUFA evidence /15": 15,
        "Market activity /10": market, "As of Pacific": "2026-10-13",
    }


def run(rows, *, fresh=True, events=None):
    if events is None:
        events = {
            r["Exact event"]: {"conflict_flag": "NONE", "new_dilution_flag": "NO"}
            for r in rows
        }
    with patch("gem_scans.build_queue", return_value=(
        rows, {"feed_current": fresh, "as_of": "2026-10-13"},
    )), patch("gem_scans._event_map", return_value=events):
        return build_gem_scans("fake-path")



class GemScanRegressionTests(__import__('unittest').TestCase):
    def test_all_three_stage_scores_are_independent_and_labeled(self):
        rows, status = run([sample(market=10), sample("BBB", market=7)])
        assert len(STAGES) == 3
        assert all(sum(weights.values()) == 100 for weights in WEIGHTS.values())
        assert rows[0]["Phase 3 GEM"] == "#1 (100)"
        assert rows[0]["Post-Financing GEM"] == "#1 (100)"
        assert rows[0]["PDUFA GEM"] == "#1 (100)"
        assert rows[1]["Phase 3 GEM"] == "#2 (96)"
        assert rows[1]["Post-Financing GEM"] == "#2 (97)"
        assert rows[1]["PDUFA GEM"] == "#2 (96)"
        assert all(status["scan_counts"][stage]["qualified"] == 2 for stage in STAGES)


    def test_financing_is_only_scored_when_exact_second_closing_verified(self):
        rows, _ = run([sample(second=False)])
        assert rows[0]["Phase 3 rank"] == 1
        assert rows[0]["Post-Financing score"] is None
        assert "Second separate" in rows[0]["Post-Financing missing"]


    def test_pdufa_timing_blocks_late_or_distant_events(self):
        rows, _ = run([sample(days=14), sample("BBB", days=91)])
        assert all(r["PDUFA rank"] is None for r in rows)
        assert rows[0]["Phase 3 rank"] is not None  # Phase 3 ranking has its own window
        assert rows[1]["Phase 3 rank"] is not None


    def test_stale_and_unrated_feeds_have_no_gem_ranks(self):
        stale, _ = run([sample()], fresh=False)
        assert all(stale[0][stage + " score"] is None for stage in STAGES)
        unrated = sample()
        unrated["Evidence score /100"] = None
        rows, _ = run([unrated])
        assert all(rows[0][stage + " rank"] is None for stage in STAGES)


    def test_conflicting_regulatory_evidence_fail_closed(self):
        row = sample()
        rows, _ = run([row], events={
            row["Exact event"]: {"conflict_flag": "REVIEW", "new_dilution_flag": "NO"}
        })
        assert all(rows[0][stage + " rank"] is None for stage in STAGES)


    def test_dilution_flag_blocks_financing_and_pdufa_but_not_phase3_research(self):
        row = sample()
        rows, _ = run([row], events={
            row["Exact event"]: {"conflict_flag": "NONE", "new_dilution_flag": "UNKNOWN"}
        })
        assert rows[0]["Phase 3 rank"] == 1
        assert rows[0]["Post-Financing rank"] is None
        assert rows[0]["PDUFA rank"] is None


    def test_equal_scores_share_rank_without_dropping_candidates(self):
        rows, _ = run([sample(), sample("BBB"), sample("CCC", market=7)])
        assert [r["Phase 3 rank"] for r in rows] == [1, 1, 3]


    def test_original_scans_and_protected_controls_are_preserved(self):
        source = (ROOT / "nightly_scan_dashboard.py").read_text(encoding="utf-8")
        assert "render_gem_scans()" in source
        assert "render_extended_source_report()" in source
        assert 'st.markdown("## NIGHTLY SCAN REPORT")' in source
        assert "PDUFA_SCAN_CONTROL_PIN" in source
        assert 'dispatch_action(action, scan, token)' in source
        ui = (ROOT / "gem_scans_ui.py").read_text(encoding="utf-8")
        assert 'colspan="3">GEMS' in ui
        assert 'rowspan="2">Ticker' in ui
        assert "Phase 3</th><th>Post-Financing</th><th>PDUFA" in ui

