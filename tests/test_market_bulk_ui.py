"""Ensure all-ticker scan is wired to its own page and never PRE PHASE 3."""
from supported_dashboard_checks import run_frontend_contract
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

    def test_supported_pipeline_research_reads_cannot_trigger_writes_or_orders(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('research-only-backend.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('read-only-warm-retry.test.cjs'), 0)


if __name__ == "__main__":
    unittest.main()
