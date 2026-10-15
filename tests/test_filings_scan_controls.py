"""Offline authorization, dispatch and rendered four-button behavior."""
import json
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from filings_scan_controls import authorized, dispatch_section_scan, section_run
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

    def test_render_and_click_do_not_launch_any_other_scan(self):
        app = AppTest.from_string(
            "from filings_base_amendments_ui import render_filings_base_amendments\n"
            "render_filings_base_amendments()\n", default_timeout=30)
        app.secrets["PDUFA_GITHUB_TOKEN"] = "server-token"
        app.secrets["PDUFA_SCAN_CONTROL_PIN"] = "1234"
        empty = pd.DataFrame(columns=["event_key", "ticker", "category", "claim"])
        with patch("filings_scan_controls.section_runs", return_value=([], "")), \
                patch("filings_base_amendments_ui.published_filings_files", return_value=(None, "")), \
                patch("filings_base_amendments_ui.required_issue_queue", return_value=(empty, "")), \
                patch("filings_scan_controls.dispatch_section_scan") as submit:
            app.run()
            self.assertFalse(app.exception)
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
