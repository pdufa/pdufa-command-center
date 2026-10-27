"""Offline authorization, dispatch and rendered four-button behavior."""
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from filings_scan_controls import authorized, dispatch_section_scan, section_run
from pipeline_universe import COLUMNS
from scripts.filings_section_scan import SECTIONS


class SectionControlTests(unittest.TestCase):
    def test_auth_is_required_at_the_dispatch_boundary(self):
        for token, pin, supplied in (("", "pin", "pin"), ("token", "", ""), ("token", "pin", "wrong")):
            with patch("filings_scan_controls.urllib.request.urlopen") as send:
                with self.assertRaises(PermissionError):
                    dispatch_section_scan("SEC_BASE", token, pin, supplied)
                send.assert_not_called()
        self.assertFalse(authorized("token", "pin", "wrong"))
        self.assertTrue(authorized("token", "pin", "pin"))

    def test_each_request_dispatches_only_the_selected_section(self):
        for section in SECTIONS:
            response = MagicMock()
            response.__enter__.return_value.status = 204
            with patch("filings_scan_controls.urllib.request.urlopen", return_value=response) as send:
                dispatch_section_scan(section, "server-token", "pin", "pin")
            request = send.call_args.args[0]
            self.assertEqual(json.loads(request.data), {"ref": "main", "inputs": {"section": section}})
            self.assertIn("pdufa-filings-section-scan.yml/dispatches", request.full_url)
        with self.assertRaises(ValueError):
            dispatch_section_scan("ALL", "server-token", "pin", "pin")

    def test_section_status_does_not_borrow_another_sections_success(self):
        runs = [{"display_title": "FDA_BASE — manual filings scan", "created_at": "2026-10-15T20:00:00Z"},
                {"display_title": "SEC_BASE — manual filings scan", "created_at": "2026-10-15T18:00:00Z"}]
        self.assertEqual(section_run(runs, "SEC_BASE"), runs[1])
        self.assertEqual(section_run(runs, "SEC_AMENDMENTS"), {})

    def test_sec_fda_controls_match_vertical_card_preview(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        filings = (root / "filings_base_amendments_ui.py").read_text(encoding="utf-8")
        controls = (root / "filings_scan_controls.py").read_text(encoding="utf-8")
        scans = (root / "nightly_scan_dashboard.py").read_text(encoding="utf-8")

        self.assertIn('st.markdown("# SEC & FDA SCAN CONTROLS")', filings)
        self.assertIn('st.markdown("Scan any section whenever needed.")', filings)
        self.assertNotIn('sec_column, fda_column = st.columns(2, gap="large")', filings)
        labels = (
            "pdufa_sec_base_card", "pdufa_sec_amend_card",
            "pdufa_fda_base_card", "pdufa_fda_amend_card",
            "pdufa_missing_evidence_card", "pdufa_scan_progress",
        )
        locations = [filings.index('with st.container(border=True, key="' + x + '")')
                     for x in labels]
        self.assertEqual(locations, sorted(locations))
        self.assertLess(filings.index('st.markdown("## SEC FINANCING")'),
                        locations[0])
        self.assertLess(filings.index('st.markdown("## FDA FILINGS")'),
                        locations[2])
        self.assertEqual(filings.count('compact=True)'), 4)
        self.assertEqual(filings.count('render_section_scan("SEC_BASE"'), 1)
        self.assertEqual(filings.count('render_section_scan("FDA_BASE"'), 1)
        self.assertEqual(filings.count('render_section_scan("SEC_AMENDMENTS"'), 1)
        self.assertEqual(filings.count('render_section_scan("FDA_AMENDMENTS"'), 1)
        for title in ("SEC Base details", "SEC Amendment details",
                      "FDA Base details", "FDA Amendment details"):
            self.assertIn(f'st.expander("{title}"', filings)
        # Exactly two agency-specific missing evidence dropdowns in one card.
        gaps = filings[locations[4]:locations[5]]
        self.assertIn('render_missing_research("SEC"', gaps)
        self.assertIn('render_missing_research(\n            "FDA"', gaps)
        self.assertIn("Ready  →  Queued  →  Running  →  Finished", filings)
        self.assertIn('status_col, button_col = st.columns(', controls)
        self.assertIn('st.button("▶ Scan this section"', controls)
        self.assertIn("@st.fragment(run_every=60)", filings)
        self.assertIn('col_a.metric("Pipeline filtered total"', filings)
        self.assertEqual(scans.count("    render_filings_base_amendments()"), 1)
        self.assertLess(scans.index("    render_filings_base_amendments()"),
                        scans.index('    st.markdown("### GEMS — GITHUB SCAN LOGS")'))

    def test_render_and_click_do_not_launch_any_other_scan(self):
        app = AppTest.from_string(
            "from filings_base_amendments_ui import render_filings_base_amendments\n"
            "render_filings_base_amendments()\n", default_timeout=30)
        app.secrets["PDUFA_GITHUB_TOKEN"] = "server-token"
        app.secrets["PDUFA_SCAN_CONTROL_PIN"] = "1234"
        # This test exercises authorization and section-specific button state,
        # not the changing repository-wide publication. Mock at the complete
        # loader boundaries: returning None from published_filings_files used
        # to fall through to thousands of real Pipeline/SEC source rows and
        # turned a four-button unit test into an unbounded bulk reconciliation.
        universe = pd.DataFrame([
            {"record_id": "TRIAL|NCT00000001", "record_type": "TRIAL",
             "ticker": "TEST", "nct_id": "NCT00000001",
             "current_stage": "Phase 3", "registered_phase": "Phase 3"},
            {"record_id": "TRIAL|NCT00000002", "record_type": "TRIAL",
             "ticker": "TEST", "nct_id": "NCT00000002",
             "current_stage": "Phase 3", "registered_phase": "Phase 3"},
        ], columns=COLUMNS, dtype=object).fillna("")
        details = {
            "sec": [], "verified": [], "extensions": [],
            "bases": {"SEC": [], "FDA": []},
            "tables": {name: [] for name in (
                "SEC Base", "SEC Amendments", "FDA Base", "FDA Amendments")},
            "queue": [], "queue_notice": "", "registry": [],
            "notes": [], "reports": {}, "refresh_notice": "",
        }
        with patch("filings_scan_controls.section_runs", return_value=([], "")), \
                patch("filings_base_amendments_ui.load_section_details", return_value=details), \
                patch("filings_base_amendments_ui.current_pipeline_universe", return_value=universe), \
                patch("filings_base_amendments_ui.published_filings_files",
                      side_effect=AssertionError("Control test must not fetch source publications")), \
                patch("filings_base_amendments_ui.required_issue_queue",
                      side_effect=AssertionError("Control test must not load the live issue queue")), \
                patch("filings_scan_controls.time", SimpleNamespace(
                    time=lambda: 1_700_000_000,
                    strftime=time.strftime, gmtime=time.gmtime)), \
                patch("filings_scan_controls.dispatch_section_scan") as submit:
            app.run()
            self.assertFalse(app.exception)
            self.assertEqual(
                [(metric.label, metric.value) for metric in app.metric],
                [("Pipeline filtered total", "2"),
                 ("SEC baseline rows", "2"), ("FDA baseline rows", "2")],
            )
            labels = [item.label for item in app.expander]
            self.assertEqual(len(labels), 6)
            for label in ("SEC Base details", "SEC Amendment details", "FDA Base details", "FDA Amendment details"):
                self.assertIn(label, labels)
            self.assertTrue(any("SEC MISSING EVIDENCE" in label for label in labels))
            self.assertTrue(any("FDA MISSING EVIDENCE" in label for label in labels))
            self.assertEqual(len([b for b in app.button if b.label == "▶ Scan this section"]), 4)
            self.assertTrue(all(app.button(key="scan_section_" + s).disabled for s in SECTIONS))
            submit.assert_not_called()
            app.text_input(key="filings_scan_control_pin").set_value("1234").run()
            self.assertFalse(app.exception)
            self.assertTrue(all(not app.button(key="scan_section_" + s).disabled for s in SECTIONS))
            app.button(key="scan_section_SEC_AMENDMENTS").click().run()
            self.assertFalse(app.exception)
            submit.assert_called_once_with("SEC_AMENDMENTS", "server-token", "1234", "1234")
            app.run()
            self.assertTrue(app.button(key="scan_section_SEC_AMENDMENTS").disabled)
            self.assertFalse(app.button(key="scan_section_FDA_BASE").disabled)
            submit.assert_called_once()


if __name__ == "__main__":
    unittest.main()
