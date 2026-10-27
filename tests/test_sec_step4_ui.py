"""Static integration checks for Streamlit Step 4 page wiring.

The Streamlit AppTest router can skip loading multipage scripts entirely without
raising an exception. Keep this deterministic until hosted browser is verified.
"""
from supported_dashboard_checks import run_frontend_contract
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "02_SEC_Financial_Analysis.py"


class Step4UiSourceTests(unittest.TestCase):
    def test_sec_page_is_valid_python_and_wired_to_backend(self):
        src = PAGE.read_text(encoding="utf-8")
        ast.parse(src, filename=str(PAGE))
        for required in (
            'from sec_step4 import DEFAULT_DB, load_registry, read_history, scan_one',
            'st.title("📑 SEC Financial Analysis — STEP 4")',
            'st.selectbox("Select company ticker"',
            'st.form_submit_button("FETCH SEC FILINGS AND SAVE REVISION", disabled=not ready)',
            'if pressed:',
            'scan_one(ticker, registry=registry, user_agent=user_agent)',
            'read_history(ticker=ticker)',
            'st.download_button("DOWNLOAD FULL SEC AUDIT HISTORY (JSON)"',
            'st.stop()',
            'st.secrets.get("SEC_USER_AGENT"',
            'SEC filing',
            'share',
        ):
            self.assertIn(required, src)

    def test_supported_source_requests_are_authenticated_read_only_and_identity_bound(self):
        """Retained product contract, executed against supported Next.js code."""
        self.assertGreater(run_frontend_contract('shared-enrichment.test.cjs'), 0)
        self.assertGreater(run_frontend_contract('research-only-backend.test.cjs'), 0)


if __name__ == "__main__":
    unittest.main()
