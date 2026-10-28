import unittest
from scripts.summarize_fda_discovery import summarize


class DiscoverySummaryTests(unittest.TestCase):
    def test_extrapolated_expansion_not_counted_as_model_eligible(self):
        result = summarize({"records": [
            {"review_status": "INDICATION_EXPANSION_EXTRAPOLATED_EVIDENCE_ACTION_LETTER_REQUIRED"},
            {"review_status": "IDENTITY_AND_ACTION_LETTER_REQUIRED"},
        ]})
        self.assertEqual(result["discovered"], 2)
        self.assertEqual(result["categories"]["EXTRAPOLATED_INDICATION_EXPANSION"], 1)
        self.assertEqual(result["independently_verified"], 0)
        self.assertEqual(result["model_eligible"], 0)

    def test_invalid_rows_rejected(self):
        with self.assertRaises(ValueError):
            summarize({"records": [None]})
