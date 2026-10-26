import sys
from datetime import datetime, timezone
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh_phase3_130_nasdaq_research import parse_cap, extract_summary, collect

class NasdaqSourceResearchTests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(parse_cap("$1.5B"), 1_500_000_000)
        self.assertEqual(parse_cap("300,000,000"), 300_000_000)
        self.assertIsNone(parse_cap("N/A"))
        self.assertIsNone(parse_cap("-100"))
    def test_reject_unknown_payload(self):
        self.assertEqual(extract_summary({"data":{"summaryData":{}}})[1], "MISSING_MARKETCAP_FIELD")
        self.assertEqual(extract_summary({"data":{"summaryData":{"MarketCap":{"value":"$2.5B"}}}})[0],2_500_000_000)
    def test_exact_130_with_source_errors_never_promotes(self):
        tickers = [f"A{chr(65+n//26)}{chr(65+n%26)}" for n in range(130)]
        def fetch(url):
            if "AAA" in url:
                return b'{"data":{"summaryData":{"MarketCap":{"value":"$2B"}}}}',200,"application/json",url
            raise OSError("network denied")
        report=collect(tickers,fetch,lambda:datetime(2026,10,26,tzinfo=timezone.utc))
        self.assertEqual(report["source_attempts"],130)
        self.assertEqual(report["source_market_caps_parsed"],1)
        self.assertEqual(report["source_errors_or_unparsed"],129)
        self.assertEqual(report["independently_verified_quote_asof"],0)
        self.assertIsNone(report["qualified_pipeline_count"])
        self.assertTrue(all(r["qualified_pipeline"] is None for r in report["issuer_rows"]))
if __name__=="__main__":
    unittest.main()
