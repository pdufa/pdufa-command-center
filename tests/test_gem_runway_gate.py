"""Financial-runway evidence is mandatory for post-financing and PDUFA GEM."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from gem_runway_gate import PASS, HOLD, REVIEW, assess_runway, load_snapshots


def sample(cash=140_000_000):
    return {
        "ticker": "TEST", "cik": "0000000123", "as_of": "2026-10-13",
        "cash_usd": cash, "operating_cash_flow_usd": -30_000_000,
        "operating_cash_flow_months": 3, "runway_months_cash_only": cash/10_000_000,
        "cash_includes_restricted": False, "review_flags": [],
        "evidence": {
            "companyfacts_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json",
            "cash": {"form": "10-Q", "accession": "0000000123-26-000001",
                     "period_end": "2026-09-30", "filed": "2026-10-10"},
            "operating_cash_flow": {"form": "10-Q", "accession": "0000000123-26-000001",
                                    "period_end": "2026-09-30", "filed": "2026-10-10"},
        }
    }


class RunwayGateTests(unittest.TestCase):
    def evaluate(self, snap):
        return assess_runway("TEST", snap, as_of=date(2026, 10, 13),
                             second_close="2026-09-15")

    def test_current_post_financing_cash_pass_and_low_cash_hold(self):
        self.assertEqual(self.evaluate(sample())["Cash runway gate"], PASS)
        self.assertEqual(self.evaluate(sample())["Cash runway (months)"], 14.0)
        self.assertEqual(self.evaluate(sample(110_000_000))["Cash runway gate"], HOLD)

    def test_missing_stale_conflicting_or_fake_source_is_never_a_pass(self):
        valid = sample()
        attempts = [None, {**valid, "ticker": "WRONG"},
                    {**valid, "as_of": "2026-10-01"},
                    {**valid, "as_of": "2026-10-14"},
                    {**valid, "cash_includes_restricted": True},
                    {**valid, "review_flags": ["report stale"]},
                    {**valid, "runway_months_cash_only": 999},
                    {**valid, "operating_cash_flow_usd": 0},
                    {**valid, "evidence": {**valid["evidence"],
                                          "companyfacts_url": "https://example.com/"}},
                    {**valid, "evidence": {**valid["evidence"],
                                          "cash": {**valid["evidence"]["cash"],
                                                   "period_end": "2026-06-30"}}}]
        for value in attempts:
            with self.subTest(value=value):
                self.assertEqual(self.evaluate(value)["Cash runway gate"], REVIEW)

    def test_identical_duplicate_snapshots_cannot_be_falsely_qualified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "gem_runway_evidence.json"
            report = {"schema_version": 1, "source": "SEC_STEP4_COMPANYFACTS",
                      "snapshots": [sample()]}
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertIn("TEST", load_snapshots(tmp))
            report["snapshots"].append(sample())
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertNotIn("TEST", load_snapshots(tmp))


if __name__ == "__main__":
    unittest.main()
