"""Search engines are discovery-only; exact SEC primary evidence still required."""
import unittest
from urllib.parse import parse_qs, urlsplit

from sec_search_discovery import financing_discovery_links


class SecSearchDiscoveryTests(unittest.TestCase):
    def test_three_engines_scoped_to_exact_issuer_sec_cik(self):
        links = financing_discovery_links(
            "DYN", "Dyne Therapeutics, Inc.", "0001818794", "10-Q"
        )
        self.assertEqual(
            set(links),
            {"Yahoo SEC", "Bing SEC", "Google SEC", "Yahoo Finance release"},
        )
        self.assertEqual(urlsplit(links["Yahoo SEC"]).hostname, "search.yahoo.com")
        self.assertEqual(urlsplit(links["Bing SEC"]).hostname, "www.bing.com")
        self.assertEqual(urlsplit(links["Google SEC"]).hostname, "www.google.com")
        for engine, url in links.items():
            parsed = urlsplit(url)
            self.assertEqual(parsed.scheme, "https")
            key = "p" if engine.startswith("Yahoo") else "q"
            q = parse_qs(parsed.query)[key][0]
            self.assertIn('"Dyne Therapeutics, Inc."', q)
            if engine.endswith("SEC"):
                self.assertIn("site:sec.gov/Archives/edgar/data/1818794/", q)
                self.assertIn('"10-Q"', q)
                self.assertIn('"completed"', q)
                self.assertNotIn("finance.yahoo.com", q)
            else:
                self.assertIn("site:finance.yahoo.com", q)
                self.assertIn('"announces closing"', q)
                self.assertNotIn("site:sec.gov", q)

    def test_exhibit_types_available_for_bing_and_yahoo(self):
        for form in ("8-K", "10-Q", "10-K", "EX-99.1", "EX-10"):
            links = financing_discovery_links(
                "MLYS", "Mineralys Therapeutics, Inc.", "0001933414", form
            )
            for engine in ("Yahoo SEC", "Bing SEC", "Google SEC"):
                q = parse_qs(urlsplit(links[engine]).query)
                self.assertIn(f'"{form}"', next(iter(q.values()))[0])

    def test_search_result_never_becomes_a_verified_financing(self):
        links = financing_discovery_links("INO", "Inovio Pharmaceuticals", "1055726")
        self.assertTrue(all(isinstance(x, str) for x in links.values()))
        self.assertNotIn("verification_status", links)
        self.assertNotIn("trade_entry_authorized", links)
        self.assertNotIn("financing_close_date", links)

    def test_invalid_company_identity_rejected(self):
        for ticker, company, cik, form in (
            ("DYN", "Dyne Therapeutics", "0", "8-K"),
            ("DYN", "Dyne Therapeutics", "../123", "8-K"),
            ("DYN", "Dyne Therapeutics", "1818794", "S-3"),
            ("DYN\nSEC", "Dyne Therapeutics", "1818794", "8-K"),
            ("DYN", "Dyne\nTherapeutics", "1818794", "8-K"),
        ):
            with self.subTest(ticker=ticker, cik=cik, form=form):
                with self.assertRaises(ValueError):
                    financing_discovery_links(ticker, company, cik, form)


if __name__ == "__main__":
    unittest.main()
