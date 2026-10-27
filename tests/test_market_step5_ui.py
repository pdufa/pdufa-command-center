"""Step 5 page integration regression; avoids multipage AppTest router redirects."""
from supported_dashboard_checks import run_frontend_contract
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "pages" / "03_Market_Intelligence.py"


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

    def test_supported_market_research_requires_exact_identity_and_read_only_boundaries(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('research-only-backend.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('research-readiness.test.cjs'), 0)


if __name__ == "__main__":
    unittest.main()
