"""Source-discovery wiring for the exact AGIO mitapivat sickle-cell PDUFA event."""
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.source_verification import Verifier


ROOT = Path(__file__).resolve().parents[1]
EVENT_KEY = "AGIO|MITAPIVAT_SCD_20261101"
URL = ("https://investor.agios.com/news-releases/news-release-details/"
       "us-fda-grants-priority-review-agios-snda-mitapivat-sickle-cell")
COMPANY = {"ticker": "AGIO", "company": "Agios Pharmaceuticals, Inc.",
           "cik10": "0001439222"}
EVENT = {"event_key": EVENT_KEY, "ticker": "AGIO",
         "company": COMPANY["company"], "drug": "mitapivat",
         "indication": "sickle cell disease", "pdufa_date": "2026-11-01"}


class AgiosPrimaryTargetMappingTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / "config/issuer_sources.json").read_text())

    def verifier(self, text):
        return Verifier([COMPANY], issuer_sources=self.config,
                        fetch=lambda _: text.encode("utf-8"),
                        as_of=date(2026, 10, 14))

    def test_exact_event_mapping_only_supplies_discovery(self):
        mapped = self.config["AGIO"]["events"][EVENT_KEY]
        self.assertEqual(mapped["urls"], [URL])
        self.assertNotIn("fda_approval", mapped)
        self.assertNotIn("verified", mapped)
        self.assertNotIn("decision_status", mapped)
        verifier = self.verifier("Placeholder with no claim")
        self.assertEqual(verifier.primary(EVENT, URL), "ISSUER")
        self.assertEqual(verifier.event_sources(EVENT), mapped)
        self.assertIn(URL, verifier.references(EVENT))

    def test_claim_still_requires_live_page_program_identity_and_explicit_date(self):
        claim = ("Agios Pharmaceuticals, Inc. mitapivat for sickle cell disease. "
                 "FDA’s PDUFA goal date is November 1, 2026.")
        good = self.verifier(claim).regulatory(EVENT, _discovery_only=True)[0]
        self.assertEqual(good["verification_status"], "VERIFIED")
        self.assertEqual(good["observed"], "2026-11-01")
        self.assertEqual(good["source_url"], URL)
        self.assertEqual(len(good["source_sha256"]), 64)
        for wrong in (
            "Agios Pharmaceuticals, Inc. mitapivat for pyruvate kinase deficiency. "
            "FDA’s PDUFA goal date is November 1, 2026.",
            "Agios Pharmaceuticals, Inc. mitapivat for sickle cell disease. "
            "FDA’s PDUFA goal date is November 8, 2026.",
            "Another issuer mitapivat for sickle cell disease. "
            "FDA’s PDUFA goal date is November 1, 2026.",
        ):
            with self.subTest(wrong=wrong):
                status = self.verifier(wrong).regulatory(EVENT, _discovery_only=True)[0]
                self.assertNotEqual(status["verification_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
