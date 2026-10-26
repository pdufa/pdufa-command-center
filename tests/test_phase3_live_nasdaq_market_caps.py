import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_live_nasdaq_market_caps import parse_market_cap, audit, LOW, HIGH

class OriginalNasdaqCapTests(unittest.TestCase):
    def test_original_numeric_summary(self):
        self.assertEqual(parse_market_cap({"data":{"summaryData":{"MarketCap":{"value":"$1,200,000,000"}}}}), 1200000000)
    def test_reject_abbreviations_and_missing(self):
        for value in ("1.2B", "N/A", "", None):
            with self.assertRaises(ValueError):
                parse_market_cap({"data":{"summaryData":{"MarketCap":{"value":value}}}})
    def test_all_130_reconciled_and_unresolved_never_promoted(self):
        def fail(ticker):
            raise ValueError("blocked")
        result = audit(fail)
        self.assertEqual(result["issuer_count"], 130)
        self.assertEqual(result["counts"]["UNRESOLVED"], 130)
        self.assertEqual(result["fresh_verified"], 0)
        self.assertIsNone(result["qualified_pipeline_count"])
        self.assertTrue(all(x["qualified_pipeline"] is None for x in result["issuers"]))
    def test_range_edges(self):
        def sample(ticker):
            return LOW, f"https://api.nasdaq.com/api/quote/{ticker}/summary?assetclass=stocks"
        result = audit(sample)
        self.assertEqual(result["counts"]["IN_RANGE"], 130)
        self.assertIsNone(result["qualified_pipeline_count"])

if __name__ == "__main__":
    unittest.main()
