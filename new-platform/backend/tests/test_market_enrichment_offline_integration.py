"""Offline integration contract: immutable registry -> mocked IEX bars -> read-only response.

No database, network, Alpaca credentials, or brokerage access is required.
"""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import read_program_market_enrichment


class _Session:
    def __init__(self, identities):
        self.identities = identities

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, model, program_number):
        return self.identities.get(program_number)


class OfflineMarketIntegrationTests(unittest.TestCase):
    def test_two_trials_same_ticker_keep_distinct_program_identities(self):
        identities = {
            165: SimpleNamespace(ticker="ABC", source_key="TRIAL|NCT00000165"),
            166: SimpleNamespace(ticker="ABC", source_key="TRIAL|NCT00000166"),
        }
        chart = {
            "status": "OK", "feed": "IEX", "coverage": "IEX ONLY",
            "asOf": "2026-10-22", "source": "https://docs.alpaca.markets/",
            "bars": [
                {"date": "2026-10-21", "close": 5.25, "volume": 100},
                {"date": "2026-10-22", "close": 5.75, "volume": 120},
            ],
        }
        with patch("app.main.Session", return_value=_Session(identities)), patch(
            "app.program_market_enrichment.get_alpaca_bars", return_value=chart
        ) as market:
            first = read_program_market_enrichment("PDUFA-000165", "1Y")
            second = read_program_market_enrichment("PDUFA-000166", "1Y")
        self.assertEqual(market.call_count, 2)
        self.assertEqual([call.args for call in market.call_args_list], [("ABC", "1Y"), ("ABC", "1Y")])
        self.assertNotEqual(first["programId"], second["programId"])
        self.assertNotEqual(first["exactKey"], second["exactKey"])
        for result in (first, second):
            self.assertEqual(result["latestDailyClose"], 5.75)
            self.assertEqual(result["latestIexVolume"], 120)
            self.assertEqual(result["barsAvailable"], 2)
            self.assertEqual(result["feed"], "IEX")
            self.assertTrue(result["researchOnly"])
            for flag in ("orderExecutionEnabled", "qualificationChanges", "restrictionChanges", "fsFaChanges"):
                self.assertFalse(result[flag])

    def test_empty_success_response_stays_empty(self):
        identities = {165: SimpleNamespace(ticker="ABC", source_key="TRIAL|NCT00000165")}
        with patch("app.main.Session", return_value=_Session(identities)), patch(
            "app.program_market_enrichment.get_alpaca_bars",
            return_value={"status": "OK", "feed": "IEX", "coverage": "IEX ONLY", "bars": []},
        ) as market:
            result = read_program_market_enrichment("PDUFA-000165", "ALL")
        market.assert_called_once_with("ABC", "ALL")
        self.assertEqual(result["status"], "OK")
        self.assertIsNone(result["latestDailyClose"])
        self.assertIsNone(result["latestIexVolume"])
        self.assertEqual(result["barsAvailable"], 0)
        self.assertFalse(result["orderExecutionEnabled"])

    def test_provider_failure_does_not_fabricate_price(self):
        identities = {165: SimpleNamespace(ticker="ABC", source_key="TRIAL|NCT00000165")}
        with patch("app.main.Session", return_value=_Session(identities)), patch(
            "app.program_market_enrichment.get_alpaca_bars",
            return_value={"status": "ALPACA_AUTH_FAILED", "feed": "IEX", "bars": []},
        ):
            result = read_program_market_enrichment("PDUFA-000165", "3M")
        self.assertEqual(result["status"], "ALPACA_AUTH_FAILED")
        self.assertIsNone(result["latestDailyClose"])
        self.assertIsNone(result["latestIexVolume"])
        self.assertEqual(result["barsAvailable"], 0)


if __name__ == "__main__":
    unittest.main()
