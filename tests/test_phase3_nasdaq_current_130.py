import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from check_phase3_nasdaq_current_130 import parse_cap,read_ticker

class NasdaqSourceTests(unittest.TestCase):
    def test_parse_cap_units_and_invalid(self):
        for raw,expected in (({"value":"$1.25B"},1.25e9),("350M",350e6),("1,250,000,000",1.25e9),(500000000,500e6)):
            self.assertEqual(parse_cap(raw),expected)
        for raw in (None,False,"N/A","--","bad","NaN","-1B"):
            self.assertIsNone(parse_cap(raw))
    def test_failed_source_does_not_qualify(self):
        with patch("check_phase3_nasdaq_current_130.urllib.request.urlopen",side_effect=TimeoutError()):
            row=read_ticker("ABCL")
        self.assertEqual(row["classification"],"SOURCE_UNVERIFIED")
        self.assertIsNone(row["qualified_pipeline"])
        self.assertFalse(row["live_quote_freshness_verified"])
    def test_retrieved_cap_cannot_certify_freshness(self):
        class Response:
            status=200
            def geturl(self):return "https://api.nasdaq.com/api/quote/ABCL/summary?assetclass=stocks"
            def read(self,n):return b'{"data":{"summaryData":{"MarketCap":{"value":"$1.1B"}}}}'
            def __enter__(self):return self
            def __exit__(self,*args):return False
        with patch("check_phase3_nasdaq_current_130.urllib.request.urlopen",return_value=Response()):
            row=read_ticker("ABCL")
        self.assertEqual(row["classification"],"SOURCE_RETRIEVED_IN_RANGE_ASOF_UNKNOWN")
        self.assertEqual(row["market_cap_usd"],1.1e9)
        self.assertFalse(row["live_quote_freshness_verified"])
        self.assertIsNone(row["qualified_pipeline"])

if __name__=="__main__":unittest.main()
