"""GEM 3 runway deterioration is advisory; the 12-month gate is independent."""
from datetime import date
import unittest

from gem_runway_trend import assess_trend


TODAY = date(2026, 10, 13)


def sec_snapshot(ticker="TEST", cash=140_000_000, period="2026-09-30",
                 filed="2026-10-10", assessed="2026-10-13"):
    return {
        "ticker": ticker, "cik": "0000000123", "as_of": assessed,
        "cash_usd": cash, "operating_cash_flow_usd": -30_000_000,
        "operating_cash_flow_months": 3,
        "runway_months_cash_only": cash / 10_000_000,
        "cash_includes_restricted": False, "review_flags": [],
        "evidence": {
            "companyfacts_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json",
            "cash": {
                "form": "10-Q", "accession": "0000000123-26-000001",
                "period_end": period, "filed": filed,
            },
            "operating_cash_flow": {
                "form": "10-Q", "accession": "0000000123-26-000001",
                "period_end": period, "filed": filed,
            },
        },
    }


class GemRunwayTrendTests(unittest.TestCase):
    def setUp(self):
        self.current = sec_snapshot()
        self.prior = sec_snapshot(
            cash=250_000_000, period="2026-06-30",
            filed="2026-08-10", assessed="2026-08-12",
        )

    def test_material_deterioration_flags_even_above_12_months(self):
        result = assess_trend("TEST", self.current, [self.prior], as_of=TODAY,
                              dilution_flag="NO")
        self.assertEqual(result["Cash runway previous (months)"], 25)
        self.assertIn("DECLINING", result["Cash runway trend"])
        self.assertIn("DESPITE 12+ MONTHS", result["GEM 3 financial alert"])

    def test_low_current_runway_always_emits_alert(self):
        low = sec_snapshot(cash=100_000_000)
        result = assess_trend("TEST", low, [self.prior], as_of=TODAY)
        self.assertIn("UNDER 12 MONTHS", result["GEM 3 financial alert"])

    def test_missing_history_does_not_fabricate_deterioration(self):
        result = assess_trend("TEST", self.current, [], as_of=TODAY)
        self.assertIsNone(result["Cash runway previous (months)"])
        self.assertIn("NO COMPARABLE", result["Cash runway trend"])
        self.assertNotIn("DETERIORATING", result["GEM 3 financial alert"])

    def test_same_quarter_and_unrelated_cik_cannot_create_trend(self):
        same = sec_snapshot(cash=400_000_000)
        wrong_cik = {**self.prior, "cik": "0000000999"}
        result = assess_trend("TEST", self.current, [same, wrong_cik], as_of=TODAY)
        self.assertIsNone(result["Cash runway previous (months)"])

    def test_new_dilution_and_unknown_dilution_are_surfaced(self):
        for flag in ("YES", "ACTIVE", "UNRESOLVED", "UNKNOWN"):
            with self.subTest(flag=flag):
                result = assess_trend("TEST", self.current, [self.prior],
                                      as_of=TODAY, dilution_flag=flag)
                self.assertIn("DILUTION", result["GEM 3 financial alert"])

    def test_invalid_current_source_does_not_use_historical_good_number(self):
        current = {**self.current, "review_flags": ["Source unavailable"]}
        result = assess_trend("TEST", current, [self.prior], as_of=TODAY)
        self.assertIsNone(result["Cash runway previous (months)"])
        self.assertIn("RUNWAY UNVERIFIED", result["GEM 3 financial alert"])


if __name__ == "__main__":
    unittest.main()
