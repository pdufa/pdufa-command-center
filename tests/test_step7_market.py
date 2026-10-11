"""Step 7 market EOD observability; no independent exchange certification."""
import unittest
from datetime import datetime, timezone, date
from scripts.step7_market_refresh import collect, market_freshness

NOW = datetime(2026, 10, 10, 18, tzinfo=timezone.utc)

class MarketFeedTests(unittest.TestCase):
    def test_calendar_stale_and_missing(self):
        self.assertEqual(market_freshness("2026-10-09", date(2026, 10, 10)), "RECENT EOD")
        self.assertEqual(market_freshness("2026-09-01", date(2026, 10, 10)), "STALE EOD")
        self.assertEqual(market_freshness("", date(2026, 10, 10)), "NO VALID PRICE SESSION")
        self.assertEqual(market_freshness("2027-10-10", date(2026, 10, 10)), "FUTURE PRICE")

    def test_volume_fields_retained_without_trading_promotion(self):
        def provider(ticker):
            return {"status":"MARKET_UPDATED","source":"https://example.org/eod",
                    "price":4.25,"last_session":"2026-10-09","last_volume":115000,
                    "prior20_volume":100000,"relative_volume":1.15,
                    "return30":12,"sessions_available":35}
        rows=collect(["ABC"],provider=provider,now=NOW,pace=0)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["relative_volume"],"1.15")
        self.assertEqual(rows[0]["last_session_freshness"],"RECENT EOD")
        self.assertNotIn("ENTRY READY", rows[0])

    def test_downstream_403_or_provider_failure_stays_missing(self):
        def bad(ticker): raise PermissionError("HTTP 403")
        rows=collect(["ABC"],provider=bad,now=NOW,pace=0)
        self.assertEqual(rows[0]["market_status"],"SOURCE_UNAVAILABLE")
        self.assertEqual(rows[0]["last_session_freshness"],"NO VALID PRICE SESSION")
        self.assertEqual(rows[0]["last_close_usd"],"")

if __name__ == "__main__":
    unittest.main()
