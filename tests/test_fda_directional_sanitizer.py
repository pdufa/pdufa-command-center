"""Regression checks for decision-safe FDA directional text handling."""
import unittest

from scripts.fda_directional_100pct import sanitize_predecision_text


class PredecisionTextTests(unittest.TestCase):
    def test_later_outcome_is_not_used(self):
        clean = sanitize_predecision_text(
            "Primary efficacy endpoint met. Later the FDA issued a CRL. "
            "Safety data require review."
        )
        self.assertIn("primary efficacy endpoint met", clean)
        self.assertIn("safety data require review", clean)
        self.assertNotIn("later the fda", clean)

    def test_eventual_outcome_is_not_used(self):
        clean = sanitize_predecision_text(
            "Trial design registered. Eventual approval followed. "
            "Primary analysis reported."
        )
        self.assertNotIn("eventual approval", clean)
        self.assertIn("primary analysis", clean)


if __name__ == "__main__":
    unittest.main()
