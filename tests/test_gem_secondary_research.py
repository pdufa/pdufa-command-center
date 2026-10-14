"""Secondary IR and social investigations never qualify GEM benchmarks."""
from __future__ import annotations

import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from gem_secondary_research import (
    CONFIRMED_INVESTOR_NEWS, OPTIONAL_CHECK_TOPICS,
    optional_check_search_links, research_search_links, source_research_policy,
)


class SecondaryGEMResearchTests(unittest.TestCase):
    def test_known_ir_sources_use_verified_issuer_destinations(self):
        expected = {
            "NTLA": "ir.intelliatx.com",
                        "CAPR": "www.capricor.com",
            "CORT": "ir.corcept.com",
            "CLDX": "ir.celldex.com",
            "MLTX": "ir.moonlaketx.com",
        }
        self.assertTrue(set(expected).issubset(CONFIRMED_INVESTOR_NEWS))
        self.assertNotIn("AXSM", CONFIRMED_INVESTOR_NEWS)
        for ticker, domain in expected.items():
            links = research_search_links({"Ticker": ticker, "Drug": "Program A"})
            self.assertEqual(urlparse(links["confirmed_issuer_news"]).hostname, domain)
            self.assertEqual(urlparse(links["sec_edgar"]).hostname, "www.sec.gov")

    def test_unknown_ticker_uses_search_not_invented_investor_domain(self):
        links = research_search_links({
            "Ticker": "ZZZZQ", "Drug": "obexelimab",
            "Indication": "autoimmune",
        })
        self.assertEqual(links["confirmed_issuer_news"], "")
        self.assertEqual(urlparse(links["find_issuer_news"]).hostname, "www.google.com")
        self.assertIn("obexelimab", parse_qs(urlparse(links["find_issuer_news"]).query)["q"][0])
        self.assertNotIn("zzzzq.com", links["find_issuer_news"])

    def test_reddit_and_clinical_searches_are_program_specific(self):
        first = research_search_links({
            "Ticker": "CLDX", "Drug": "barzolvolimab",
            "Indication": "CSU", "NCT ID": "NCT06445023",
        })
        second = research_search_links({
            "Ticker": "CLDX", "Drug": "barzolvolimab",
            "Indication": "CSU", "NCT ID": "NCT06455202",
        })
        self.assertIn("barzolvolimab", first["reddit_program"])
        self.assertIn("%24CLDX", first["reddit_program"])
        self.assertIn("NCT06445023", first["clinical_trials"])
        self.assertIn("NCT06455202", second["clinical_trials"])
        self.assertNotEqual(first["clinical_trials"], second["clinical_trials"])

    def test_secondary_sources_cannot_change_entry_benchmarks(self):
        policy = source_research_policy().upper()
        self.assertIn("NEVER", policy)
        self.assertIn("SOCIAL", policy)
        self.assertIn("SEC", policy)
        self.assertIn("#2 PIPELINE", policy)
        self.assertIn("#1 GEM", policy)
        root = Path(__file__).resolve().parents[1]
        ui = (root / "gem_potential_ui.py").read_text(encoding="utf-8")
        self.assertIn("INVESTOR RELATIONS + SOCIAL RESEARCH", ui)
        self.assertIn('source_research_policy()', ui)
        self.assertIn("st.link_button(", ui)
        self.assertIn("Reddit program discussions", ui)
        # Neither the core filter nor the two actual criteria is imported.
        engine = (root / "gem_secondary_research.py").read_text(encoding="utf-8")
        self.assertNotIn("gem_two_benchmark", engine)
        self.assertNotIn("Two-benchmark eligible", engine)
        self.assertNotIn("build_gem_scans(", engine)

    def test_all_twelve_nonbenchmark_checks_searchable_without_promotion(self):
        self.assertEqual(len(OPTIONAL_CHECK_TOPICS), 12)
        keys = {key for key, _, _ in OPTIONAL_CHECK_TOPICS}
        self.assertNotIn("phase3_verified", keys)
        self.assertNotIn("financing_verified", keys)
        for key in keys:
            urls = optional_check_search_links(
                {"Ticker": "NTLA", "Drug": "lonvo-z", "NCT ID": "NCT12345678"},
                key,
            )
            self.assertIn("www.reddit.com", urls["reddit"])
            self.assertIn("www.google.com", urls["primary_records"])
            self.assertEqual(urls["issuer_ir"],
                             CONFIRMED_INVESTOR_NEWS["NTLA"])
            self.assertIn("never PASS", urls["notice"])
        with self.assertRaises(ValueError):
            optional_check_search_links({"Ticker": "NTLA"}, "phase3_verified")

    def test_missing_ticker_is_fail_closed(self):
        self.assertEqual(research_search_links({"Drug": "something"}), {})


if __name__ == "__main__":
    unittest.main()
