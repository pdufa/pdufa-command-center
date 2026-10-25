import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_system_status_production import REQUIRED_TEXT, verify_html


class ProductionSmokeValidatorTests(unittest.TestCase):
    def test_all_fifteen_sections_are_required(self):
        self.assertEqual(len(REQUIRED_TEXT), 17)
        self.assertEqual(len(set(REQUIRED_TEXT)), 17)
        verify_html("<html>" + " ".join(REQUIRED_TEXT).replace("&", "&amp;") + "</html>")

    def test_unauthenticated_challenge_or_partial_page_fails(self):
        with self.assertRaisesRegex(ValueError, "Production page did not contain"):
            verify_html("<html><title>Authentication Required</title></html>")
        with self.assertRaisesRegex(ValueError, "Final Acceptance"):
            verify_html(" ".join(REQUIRED_TEXT).replace("Final Acceptance", ""))


if __name__ == "__main__":
    unittest.main()
