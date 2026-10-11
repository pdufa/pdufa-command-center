"""Offline regression tests for SEC Step 4: never call the real SEC here."""
from __future__ import annotations
import copy
import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from sec_step4 import (
    _http_json, _sec_files, analyze_companyfacts, cik10, clean_ticker,
    load_registry, read_history, save_snapshot, scan_one,
)

CIK = "0001234567"
FORM = "10-Q"
def entry(value, end, filed, start=None, form=FORM, accn="0001234567-26-000001"):
    item = {"val": value, "end": end, "filed": filed, "form": form, "accn": accn}
    if start is not None:
        item["start"] = start
    return item


def factset(cash=90_000_000, include_q2=True):
    cash_tags = {"CashAndCashEquivalentsAtCarryingValue":
                 {"units": {"USD": [entry(cash, "2026-06-30", "2026-08-07")]}}}
    op = [entry(-9_000_000, "2026-03-31", "2026-05-07", "2026-01-01")]
    if include_q2:
        op.append(entry(-33_000_000, "2026-06-30", "2026-08-07", "2026-01-01"))
    return {
        "cik": 1234567,
        "facts": {
            "us-gaap": {
                **cash_tags,
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": op}},
                "RevenueFromContractWithCustomerExcludingAssessedTax":
                    {"units": {"USD": [entry(6_000_000, "2026-06-30", "2026-08-07", "2026-04-01")]}},
                "LongTermDebtCurrent": {"units": {"USD": [entry(2_000_000, "2026-06-30", "2026-08-07")]}},
                "LongTermDebtNoncurrent": {"units": {"USD": [entry(10_000_000, "2026-06-30", "2026-08-07")]}},
            },
            "dei": {
                "CommonStockSharesOutstanding": {"units": {"shares": [
                    entry(50_000_000, "2026-06-30", "2026-08-07")
                ]}}
            },
        },
    }


def filings():
    return {
        "cik": 1234567,
        "filings": {"recent": {
            "form": ["424B5", "S-3", "8-K", "10-Q"],
            "filingDate": ["2026-09-11", "2026-07-04", "2026-06-25", "2026-08-07"],
            "accessionNumber": [
                "0001234567-26-000003", "0001234567-26-000002",
                "0001234567-26-000001", "0001234567-26-000004"
            ],
            "primaryDocument": ["offering.htm", "shelf.htm", "current.htm", "quarter.htm"]
        }},
    }


def report(facts=None, sub=None, as_of="2026-10-10"):
    return analyze_companyfacts("ABCD", CIK, "Test Biotech", facts or factset(),
                                sub or filings(), as_of=as_of)


class SecStep4Tests(unittest.TestCase):
    def test_identity_exact_ticker_cik_and_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "companies.csv"
            path.write_text("ticker,company,cik10\nABCD,First,1234567\nABCD,Other,9999999\nEFGH,Third,1234568\nBAD,No,0\n")
            reg = load_registry(path)
            self.assertTrue(reg["ABCD"]["conflict"])
            self.assertEqual(reg["EFGH"]["cik"], "0001234568")
            self.assertNotIn("BAD", reg)
            self.assertEqual(cik10(1234567), CIK)
            with self.assertRaises(ValueError):
                clean_ticker("ABCD?")

    def test_exact_quarter_cash_flow_uses_ytd_delta(self):
        out = report()
        self.assertEqual(out["operating_cash_flow_usd"], -24_000_000)
        self.assertEqual(out["monthly_operating_burn_usd"], 8_000_000)
        self.assertEqual(out["runway_months_cash_only"], 11.25)
        self.assertEqual(out["cash_runway_risk"], "ELEVATED — 6 TO UNDER 12 MONTHS")
        self.assertEqual(out["evidence"]["operating_cash_flow"]["basis"], "YTD LESS PRIOR YTD")
        self.assertIsNone(out["product_revenue_usd"])
        self.assertIsNone(out["financial_score_0_100"])

    def test_latest_direct_quarter_over_older_ytd_derived(self):
        obj = factset()
        obj["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"].append(
            entry(-15_000_000, "2026-09-30", "2026-10-07", "2026-07-01"))
        obj["facts"]["us-gaap"]["CashAndCashEquivalentsAtCarryingValue"]["units"]["USD"].append(
            entry(81_000_000, "2026-09-30", "2026-10-07"))
        out = report(obj)
        self.assertEqual(out["monthly_operating_burn_usd"], 5_000_000)
        self.assertEqual(out["runway_months_cash_only"], 16.2)

    def test_missing_predecessor_does_not_divide_six_month_cf_by_three(self):
        obj = factset()
        op = obj["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"]
        del op[0]
        out = report(obj)
        self.assertIsNone(out["operating_cash_flow_usd"])
        self.assertIsNone(out["runway_months_cash_only"])
        self.assertIn("MISSING", out["cash_runway_risk"])

    def test_cash_restricted_cash_cannot_count_toward_runway(self):
        obj = factset()
        obj["facts"]["us-gaap"].pop("CashAndCashEquivalentsAtCarryingValue")
        obj["facts"]["us-gaap"]["CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"] = {
            "units": {"USD": [entry(100_000_000, "2026-06-30", "2026-08-07")]}}
        out = report(obj)
        self.assertIsNone(out["runway_months_cash_only"])
        self.assertTrue(out["cash_includes_restricted"])

    def test_missing_or_stale_data_never_promoted_to_score(self):
        obj = factset()
        out = report(obj, as_of="2027-04-01")
        self.assertIsNone(out["runway_months_cash_only"])
        self.assertTrue(out["review_flags"])
        self.assertEqual(out["cash_runway_risk"], "REVIEW — MISSING OR STALE INPUTS")

    def test_zero_or_positive_operating_cash_flow_no_infinite_runway(self):
        obj = factset()
        op = obj["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"]
        op[0]["val"] = 9_000_000
        op[1]["val"] = 33_000_000
        out = report(obj)
        self.assertEqual(out["monthly_operating_burn_usd"], 0)
        self.assertIsNone(out["runway_months_cash_only"])

    def test_amended_and_future_filing_filter_and_no_fabricated_closing(self):
        out = report()
        queue = out["filing_review_queue"]
        self.assertEqual(len(queue), 3)
        self.assertTrue(queue[0]["source_url"].endswith("000123456726000003/offering.htm"))
        self.assertIn("NOT proof", queue[0]["review_note"])
        self.assertTrue(all(not q["close_verified"] for q in queue))
        self.assertIn("NOT VERIFIED", out["financing_closed"])
        future = report(as_of="2026-07-01")
        self.assertEqual(len(future["filing_review_queue"]), 1)

    def test_cik_mismatch_blocks_cross_issuer_contamination(self):
        x = factset()
        x["cik"] = 9999999
        with self.assertRaises(ValueError):
            report(x)
        bad = filings()
        bad["cik"] = 42
        with self.assertRaises(ValueError):
            report(sub=bad)

    def test_history_is_append_only_and_refresh_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "step4.sqlite3"
            base = report()
            id1 = save_snapshot(base, path)
            id2 = save_snapshot(base, path)
            changed = dict(base)
            changed["runway_months_cash_only"] = 10.5
            id3 = save_snapshot(changed, path)
            self.assertEqual((id1, id2, id3), (1, 1, 2))
            history = read_history(path, "ABCD")
            self.assertEqual(len(history), 2)
            self.assertNotEqual(history[0]["content_sha256"], history[1]["content_sha256"])

    def test_sec_403_explicit_and_missing_identity_fails_closed(self):
        def no_access(req, timeout):
            raise HTTPError(req.full_url, 403, "Forbidden", None, None)
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            _http_json("https://data.sec.gov/submissions/CIK0001234567.json",
                       "PDUFA Research test@example.org", opener=no_access)
        with self.assertRaises(ValueError):
            _http_json("https://data.sec.gov/submissions/CIK0001234567.json",
                       "", opener=no_access)
        with self.assertRaises(ValueError):
            scan_one("NOPE", registry={}, user_agent="PDUFA Research test@example.org")


if __name__ == "__main__":
    unittest.main()
