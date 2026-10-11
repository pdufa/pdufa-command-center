"""Step 5 page integration regression; avoids multipage AppTest router redirects."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "pages" / "03_Market_Intelligence.py"
PREVIOUS = ROOT / "app.py"


class Step5UiIntegrationTests(unittest.TestCase):
    def test_market_page_compiles_and_controls_are_user_triggered(self):
        source = MARKET.read_text(encoding="utf-8")
        ast.parse(source, filename=str(MARKET))
        for expected in (
            'st.title("📈 Market Intelligence & Stock Ranking — STEP 5")',
            'st.selectbox("Registered biotech ticker"',
            'with st.form("market_step5_research"):',
            'st.form_submit_button("FETCH / ANALYZE & SAVE MARKET SNAPSHOT")',
            "if analyze:",
            "fetch_stooq_daily(ticker, as_of)",
            "parse_ohlcv(uploaded.getvalue().decode",
            "evaluate_market(",
            "read_history(ticker=ticker)",
            "rankings(complete, as_of.isoformat(), phase)",
            'st.download_button("DOWNLOAD STEP 5 AUDIT HISTORY (JSON)"',
        ):
            self.assertIn(expected, source)
        before = source.split("if analyze:", 1)[0]
        self.assertNotIn("fetch_stooq_daily(ticker, as_of)", before)
        self.assertNotIn("save_snapshot(snapshot)", before)

    def test_pre_phase3_remains_blank_and_step5_does_not_inject_ui(self):
        main = PREVIOUS.read_text(encoding="utf-8")
        src = MARKET.read_text(encoding="utf-8")
        a = main.index("def render_pre_phase3():")
        b = main.index("\nquery_event =", a)
        handler = main[a:b]
        self.assertIn("_step7_snapshot(signature)", handler)
        self.assertIn('st.markdown("## PRE PHASE 3 — LIVE SOURCE MONITOR")', handler)
        self.assertNotIn("render_clinical_review()", handler)
        self.assertNotIn("market_step5", handler)
        self.assertNotIn("render_pre_phase3(", src)


if __name__ == "__main__":
    unittest.main()
