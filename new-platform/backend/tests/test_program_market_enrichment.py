"""Unit tests for immutable program-to-market enrichment mapping."""
import unittest
from unittest.mock import patch

from app.program_market_enrichment import enrich_program_market


class ProgramMarketEnrichmentTests(unittest.TestCase):
    def test_program_identity_and_provenance(self):
        chart = {
            "status": "OK", "feed": "IEX", "coverage": "IEX ONLY",
            "asOf": "2026-10-22", "source": "https://docs.alpaca.markets/",
            "bars": [{"close": 7.5, "volume": 250, "date": "2026-10-22"}],
        }
        with patch("app.program_market_enrichment.get_alpaca_bars", return_value=chart) as provider:
            result = enrich_program_market("PDUFA-000165", "EXACT|TRIAL", "abc")
        provider.assert_called_once_with("abc", "1Y")
        self.assertEqual(result["programId"], "PDUFA-000165")
        self.assertEqual(result["exactKey"], "EXACT|TRIAL")
        self.assertEqual(result["latestDailyClose"], 7.5)
        self.assertEqual(result["latestIexVolume"], 250)
        self.assertFalse(result["orderExecutionEnabled"])
        self.assertFalse(result["restrictionChanges"])
        self.assertFalse(result["fsFaChanges"])

    def test_missing_data_not_fabricated(self):
        with patch("app.program_market_enrichment.get_alpaca_bars", return_value={"status": "ALPACA_AUTH_FAILED", "bars": []}):
            result = enrich_program_market("PDUFA-000165", "EXACT", "ABC")
        self.assertIsNone(result["latestDailyClose"])
        self.assertIsNone(result["latestIexVolume"])
        self.assertEqual(result["barsAvailable"], 0)

    def test_requires_exact_identity(self):
        with self.assertRaises(ValueError):
            enrich_program_market("", "EXACT", "ABC")
        with self.assertRaises(ValueError):
            enrich_program_market("PDUFA-000165", "", "ABC")


if __name__ == "__main__":
    unittest.main()
