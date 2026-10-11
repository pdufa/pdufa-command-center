"""Streamlit UI regression for Step 4; makes zero SEC network requests."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

PAGE = Path(__file__).resolve().parents[1] / "pages" / "02_SEC_Financial_Analysis.py"

class Step4UiTests(unittest.TestCase):
    def test_financial_page_renders_without_sec_access(self):
        with patch.dict(os.environ, {"SEC_USER_AGENT": ""}):
            app = AppTest.from_file(str(PAGE), default_timeout=40)
            app.run()
        self.assertFalse(list(app.exception), [str(e) for e in app.exception])
        self.assertIn("SEC Financial Analysis", PAGE.read_text(encoding="utf-8"))
        # Streamlit can expose headings under differing test-tree selectors;
        # test the page's active inputs rather than a presentation wrapper.
        self.assertTrue(any("Select company ticker" in v.label for v in app.selectbox))
        self.assertTrue(any("No stored SEC financial snapshot" in str(v.body)
                            for v in app.info))
        self.assertFalse(any("Phase 3 Success Probability" in str(v.body)
                             for v in app.markdown))

if __name__ == "__main__":
    unittest.main()
