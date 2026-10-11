"""Static integration tests for Step 4 closing review; no remote SEC calls."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "02_SEC_Financial_Analysis.py"
CLOSURE_PAGE = ROOT / "sec_financing_closure_ui.py"
ENGINE = ROOT / "sec_financing_closure.py"


class FinancingClosureUIIntegrationTests(unittest.TestCase):
    def test_closure_review_is_on_sec_page_not_prephase(self):
        page = PAGE.read_text(encoding="utf-8")
        closure = CLOSURE_PAGE.read_text(encoding="utf-8")
        engine = ENGINE.read_text(encoding="utf-8")
        for source, path in ((page, PAGE), (closure, CLOSURE_PAGE),
                             (engine, ENGINE)):
            ast.parse(source, filename=str(path))
        self.assertIn("from sec_financing_closure_ui import render_financing_closure", page)
        self.assertIn("render_financing_closure(ticker, identity, report, user_agent, ready)", page)
        self.assertIn("SEC Financial Analysis — STEP 4", page)
        self.assertIn("with st.form(\"sec_financing_fetch_document\"):", closure)
        self.assertIn("with st.form(\"sec_financing_attest_review\"):", closure)
        self.assertIn("if fetch:", closure)
        self.assertIn("if save:", closure)
        self.assertIn("fetch_sec_document(", closure)
        self.assertIn("review_closure(", closure)
        self.assertIn("save_review(event)", closure)
        self.assertIn("financing_gate(", closure)
        self.assertIn("DOWNLOAD FINANCING CLOSURE AUDIT LEDGER", closure)
        before = closure.split("if fetch:", 1)[0]
        self.assertNotIn("fetch_sec_document(", before)

    def test_core_pre_phase3_remains_blank(self):
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        pre = app.split("def render_pre_phase3():", 1)[1].split("query_event =", 1)[0]
        self.assertIn("pass", pre)
        self.assertNotIn("sec_financing_closure", pre)
        self.assertNotIn("render_clinical_review()", pre)
        self.assertNotIn("render_financing_closure(", pre)


if __name__ == "__main__":
    unittest.main()
