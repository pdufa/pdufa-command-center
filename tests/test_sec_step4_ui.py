"""Smoke test the standalone Step 4 Streamlit script outside page-routing context."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "pages" / "02_SEC_Financial_Analysis.py"


class Step4UiTests(unittest.TestCase):
    def test_financial_page_renders_without_sec_access(self):
        self.assertIn('st.title("📑 SEC Financial Analysis — STEP 4")',
                      PAGE.read_text(encoding="utf-8"))
        # AppTest.from_file can redirect physical pages/ scripts to the
        # Streamlit multipage router, rather than running their source.
        # Copy into a temporary standalone app path for an actual UI smoke test.
        with tempfile.TemporaryDirectory(prefix="step4_smoke_", dir=str(ROOT)) as tmp:
            standalone = Path(tmp) / "sec_step4_smoke.py"
            shutil.copyfile(PAGE, standalone)
            with patch.dict(os.environ, {"SEC_USER_AGENT": ""}):
                app = AppTest.from_file(str(standalone), default_timeout=60).run()
            self.assertFalse(list(app.exception), [str(v) for v in app.exception])
            self.assertTrue(any("SEC Financial Analysis" in v.body for v in app.title),
                            "SEC title did not render in standalone script")
            self.assertTrue(any("Select company ticker" in v.label for v in app.selectbox),
                            "SEC ticker picker did not render")
            self.assertTrue(any("No stored SEC financial snapshot" in str(v.body)
                                for v in app.info),
                            "Missing-data screen must be honest when no SEC history exists")


if __name__ == "__main__":
    unittest.main()
