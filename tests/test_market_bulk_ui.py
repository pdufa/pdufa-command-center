"""Ensure all-ticker scan is wired to its own page and never PRE PHASE 3."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BulkUiTests(unittest.TestCase):
    def test_bulk_scan_wiring_and_manual_launch(self):
        page = (ROOT / "pages" / "03_Market_Intelligence.py").read_text(encoding="utf-8")
        ui = (ROOT / "market_bulk_ui.py").read_text(encoding="utf-8")
        scanner = (ROOT / "market_bulk_scan.py").read_text(encoding="utf-8")
        for name, source in (("market_bulk_ui.py", ui), ("market_bulk_scan.py", scanner)):
            ast.parse(source, filename=name)
        self.assertIn("from market_bulk_ui import render_batch_scanner", page)
        self.assertIn("render_batch_scanner(identities, date.today())", page)
        self.assertIn('st.form_submit_button("SCAN ALL REGISTERED BIOTECH STOCKS")', ui)
        self.assertIn("if launch:", ui)
        self.assertIn("run_bulk(", ui)
        self.assertIn("max_workers=workers", ui)
        self.assertIn("min_interval=spacing", ui)
        self.assertIn("on_progress=on_progress", ui)
        self.assertIn("read_bulk_results()", ui)
        self.assertIn("DOWNLOAD COMPLETE ALL-STOCK SCAN CSV", ui)
        self.assertIn("REVIEW — PHASE UNVERIFIED", scanner)
        self.assertIn("NEUTRAL_WEIGHTS", scanner)
        self.assertNotIn("run_bulk(", ui.split("if launch:", 1)[0])

    def test_prephase_3_not_rendered_and_workflow_is_manual(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        pre = app.split("def render_pre_phase3():", 1)[1].split("query_event =", 1)[0]
        self.assertIn('st.markdown("## PRE PHASE 3 — LIVE SOURCE MONITOR")', pre)
        self.assertIn("_step7_snapshot(signature)", pre)
        self.assertNotIn("market_bulk", pre)
        self.assertNotIn("render_clinical_review()", pre)
        # Prior scanner GitHub workflows were intentionally removed at the
        # user's request. The market scanner and its on-screen manual UI remain.
        self.assertFalse((ROOT / ".github" / "workflows" / "full-market-scan.yml").exists())
        self.assertTrue((ROOT / "market_bulk_scan.py").is_file())


if __name__ == "__main__":
    unittest.main()
