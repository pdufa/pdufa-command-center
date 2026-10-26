import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data/research/sva-trading-halt-review-2026-10-26.json"

class SvaHaltEvidenceTests(unittest.TestCase):
    def test_halted_stock_not_promoted_to_live_cap_or_pipeline(self):
        data = json.loads(PATH.read_text())
        self.assertEqual(data["ticker"], "SVA")
        self.assertEqual(data["finding"], "TRADING_HALT_REVIEW_REQUIRED")
        self.assertFalse(data["marketCapFromHaltedPriceIsCurrent"])
        self.assertFalse(data["liveTradingVerified"])
        self.assertFalse(data["liveMarketCapVerified"])
        self.assertIsNone(data["qualifiedPipeline"])
        self.assertGreaterEqual(len(data["haltSources"]), 2)

if __name__ == "__main__":
    unittest.main()
