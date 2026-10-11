"""Visibility and provenance regression tests for PRE PHASE 3 'p' column."""
import csv
import re
import unittest
from pathlib import Path

from phase2_pre_phase3_evidence import phase2_linked_summary, primary_evidence_index
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]


class PrePhase3PVisibilityTests(unittest.TestCase):
    def test_compact_p_preserves_comparisons_and_qualifiers(self):
        now = datetime(2026,10,10,20,tzinfo=timezone.utc)
        source = [{
            "ticker":"ABCD", "nct_id":"NCT12345678", "observation_id":"a",
            "primary_endpoint":"Primary", "comparison":"drug vs placebo",
            "p_value":"0.012", "p_value_modifier":"<",
            "results_first_posted":"2026-09-01",
            "observed_at_utc":"2026-10-10T19:00:00Z",
            "source_url":"https://clinicaltrials.gov/study/NCT12345678",
        }]
        index = primary_evidence_index(source, now)
        summary = phase2_linked_summary(index, "ABCD", "NCT12345678")
        self.assertEqual(summary["Phase 2 p"], "p<0.012")
        self.assertIn("drug vs placebo", summary["Linked Phase 2 PRIMARY p"])
        self.assertEqual(phase2_linked_summary(index, "BAD", "NCT12345678")["Phase 2 p"], "NOT VERIFIED")

    def test_p_visible_second_column_and_preview_in_app_source(self):
        app = (ROOT/"app.py").read_text(encoding="utf-8")
        view = app.split("def render_pre_phase3():",1)[1].split("query_event =",1)[0]
        self.assertIn('"Ticker", "Phase 2 p", "Drug"', view)
        self.assertIn("PHASE 2 PRIMARY p — LINKED TO PHASE 3", view)
        self.assertIn("st.table(phase2_preview.rename", view)
        self.assertIn("NOT a Phase 3 p-value or a success probability", view)

    def test_latest_saved_clinical_feed_contains_real_linked_p_values(self):
        feed = ROOT/"data/step7_pre_phase3_feed.csv"
        with feed.open(newline="",encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        self.assertGreater(len(rows),0)
        self.assertIn("Phase 2 p", rows[0])
        matched = [
            row for row in rows
            if row.get("Trial phase") in ("Phase 3","Phase 2/3")
            and row.get("Ticker") in ("TRVI","LBRX")
            and re.search(r"p(?:[<>=]+)(?:0?\\.\\d+)",row.get("Phase 2 p",""))
        ]
        self.assertGreaterEqual(len(matched),3,"Three exact-linked saved Phase 3 rows should have visible p evidence")
        self.assertTrue(all("NO" in r.get("ENTRY READY","") for r in matched))

    def test_live_browser_audit_requires_rendered_p_values(self):
        code = (ROOT/"scripts/live_streamlit_audit.cjs").read_text(encoding="utf-8")
        self.assertIn("result.checks.prePhase3Phase2PVisible",code)
        self.assertIn('phase2View.includes("p=0.0028")',code)
        self.assertIn('phase2View.includes("p=0.0009")',code)
        self.assertIn('result.errors.push("PRE PHASE 3 did not render',code)


if __name__ == "__main__":
    unittest.main()
