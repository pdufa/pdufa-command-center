import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from recheck_phase3_nasdaq_market_caps import parse_cap

class NasdaqCapParserTests(unittest.TestCase):
    def test_numeric_cap(self):
        self.assertEqual(parse_cap({"data":{"symbol":"ABCD","summaryData":{"MarketCap":{"value":"$1,250,000,000"}}}}, "ABCD"), 1250000000)
    def test_billion_suffix(self):
        self.assertEqual(parse_cap({"data":{"symbol":"ABCD","summaryData":{"MarketCap":{"value":"$1.25B"}}}}, "ABCD"), 1250000000)
    def test_wrong_ticker_fails(self):
        with self.assertRaises(ValueError):
            parse_cap({"data":{"symbol":"OTHER","summaryData":{"MarketCap":{"value":"$1B"}}}}, "ABCD")
    def test_missing_cap_fails(self):
        with self.assertRaises(ValueError):
            parse_cap({"data":{"symbol":"ABCD","summaryData":{}}}, "ABCD")
if __name__ == "__main__":
    unittest.main()
