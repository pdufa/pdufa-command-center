"""Offline parse and fetch safety checks for Stock Analysis dated market caps."""
from __future__ import annotations
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from p3_market_cap_secondary import BackupCapError, parse_source, lookup_missing_primary, fetch_source, SOURCE

TICKER="CAPR"
def fixture(day=None, ticker=TICKER, amount="$523.25 million", extra=""):
    day=day or date.today()
    formatted=f"{day:%B} {day.day}, {day.year}"
    return (f"<html><head><title>Capricor Therapeutics ({ticker}) Market Cap &amp; Net Worth</title></head>"
            f"<body><h1>Capricor Therapeutics Market Cap</h1>"
            f"<p>Capricor Therapeutics has a market cap or net worth of {amount} as of {formatted}. "
            f"Historical and live market cap information.</p>{extra}</body></html>")


class SecondaryCapTests(unittest.TestCase):
    def test_parse_exact_ticker_and_asof_rounded_source_quote(self):
        cutoff=date.today()
        amount, day, url=parse_source(fixture(cutoff),TICKER,cutoff)
        self.assertEqual(amount,523250000)
        self.assertEqual(day,cutoff.isoformat())
        self.assertEqual(url,SOURCE.format(ticker=TICKER.lower()))

    def test_different_symbol_never_accepted(self):
        with self.assertRaisesRegex(BackupCapError,"SYMBOL_MISMATCH"):
            parse_source(fixture(ticker="ZBIO"),TICKER,date.today())

    def test_redirect_url_disallowed(self):
        with self.assertRaisesRegex(BackupCapError,"SOURCE_REDIRECT"):
            parse_source(fixture(),TICKER,date.today(),url="https://example.com")

    def test_missing_or_ambiguous_market_cap_rejected(self):
        with self.assertRaisesRegex(BackupCapError,"NO_UNIQUE"):
            parse_source(fixture().replace("has a market cap or net worth of", "had a cap of"),TICKER,date.today())
        p="<p>Capricor Therapeutics has a market cap or net worth of $1.40 billion as of "
        d=date.today()
        extra=p+f"{d:%B} {d.day}, {d.year}.</p>"
        with self.assertRaisesRegex(BackupCapError,"NO_UNIQUE"):
            parse_source(fixture(extra=extra),TICKER,date.today())

    def test_future_and_stale_source_rejected(self):
        today=date.today()
        with self.assertRaisesRegex(BackupCapError,"TOO_OLD_OR_FUTURE"):
            parse_source(fixture(today-timedelta(days=7)),TICKER,today)
        with self.assertRaisesRegex(BackupCapError,"TOO_OLD_OR_FUTURE"):
            parse_source(fixture(today+timedelta(days=1)),TICKER,today)

    def test_out_of_scope_market_cap_never_accepted(self):
        with self.assertRaisesRegex(BackupCapError,"OUTSIDE_300M_TO_10B"):
            parse_source(fixture(amount="$40.00 million"),TICKER,date.today())
        with self.assertRaisesRegex(BackupCapError,"OUTSIDE_300M_TO_10B"):
            parse_source(fixture(amount="$10.01 billion"),TICKER,date.today())

    def test_html_heading_company_identity_enforced(self):
        with self.assertRaisesRegex(BackupCapError,"ISSUER_NAME_MISMATCH"):
            parse_source(fixture().replace("<h1>Capricor", "<h1>Different"),
                         TICKER,date.today())

    def test_secondary_lookup_is_unique_per_issuer(self):
        called=[]
        def fetch(ticker, cutoff):
            called.append(ticker)
            if ticker=="ZBIO": raise BackupCapError("SOURCE_UNAVAILABLE")
            return (523250000, cutoff.isoformat(),SOURCE.format(ticker=ticker.lower()))
        resolved,errors=lookup_missing_primary({"CAPR","CAPR","ZBIO"},date.today(),fetch=fetch)
        self.assertEqual(called,["CAPR","ZBIO"])
        self.assertEqual(set(resolved),{"CAPR"})
        self.assertEqual(errors,{"ZBIO":"SOURCE_UNAVAILABLE"})

    def test_bad_content_type_or_non200_never_used(self):
        class Response:
            status_code=200
            url=SOURCE.format(ticker="capr")
            content=b"<html></html>"
            text="<html></html>"
            headers={"content-type":"application/json"}
        def fake(*args,**kwargs): return Response()
        with self.assertRaisesRegex(BackupCapError,"NOT_HTML"):
            fetch_source("CAPR",date.today(),fetcher=fake)


if __name__ == "__main__":
    unittest.main()
