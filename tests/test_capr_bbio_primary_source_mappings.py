"""Keep exact-event source discovery separate from regulatory approval decisions.

Primary source URLs are leads only; fetched text must match the actual drug,
indication, issuer and explicit PDUFA target. Never change saved verification
ledgers or trade eligibility from a link being configured.
"""
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.source_verification import Verifier


ROOT = Path(__file__).resolve().parents[1]
CAPR_KEY = "CAPR|DERAMIOCEL_DMD_20261122"
BBIO_KEY = "BBIO|BBP418_LGMD2IR9_20261127"
CAPR_URL = ("https://www.capricor.com/investors/news-events/press-releases/"
            "detail/354/capricor-therapeutics-announces-extension-of-pdufa-target")
BBIO_URL = ("https://investor.bridgebio.com/news/news-details/2026/"
            "BridgeBio-Announces-FDA-Acceptance-and-Priority-Review-of-NDA-"
            "for-BBP-418-for-LGMD2IR9/default.aspx")
CAPR = {"event_key": CAPR_KEY, "ticker": "CAPR",
        "company": "CAPRICOR THERAPEUTICS, INC.", "drug": "Deramiocel",
        "indication": "Duchenne muscular dystrophy (DMD)",
        "pdufa_date": "2026-11-22"}
BBIO = {"event_key": BBIO_KEY, "ticker": "BBIO",
        "company": "BridgeBio Pharma, Inc.", "drug": "BBP-418",
        "indication": "LGMD2I/R9", "pdufa_date": "2026-11-27"}


class PrimaryIssuerEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config/issuer_sources.json").read_text())
        cls.companies = [
            {"ticker": "CAPR", "company": CAPR["company"], "cik10": "0001133869"},
            {"ticker": "BBIO", "company": BBIO["company"], "cik10": "0001743881"},
        ]

    def verifier(self, content):
        return Verifier(self.companies, issuer_sources=self.config,
                        fetch=lambda url: content.encode("utf-8"),
                        as_of=date(2026, 10, 14))

    def test_both_links_are_exact_event_discovery_only(self):
        for event, url in ((CAPR, CAPR_URL), (BBIO, BBIO_URL)):
            with self.subTest(ticker=event["ticker"]):
                config = self.config[event["ticker"]]["events"][event["event_key"]]
                self.assertEqual(config["urls"], [url])
                for forbidden in ("verified", "fda_approval", "outcome",
                                  "decision_status", "entry_ready"):
                    self.assertNotIn(forbidden, config)
                verifier = self.verifier("Unrelated page")
                self.assertEqual(verifier.primary(event, url), "ISSUER")
                self.assertIn(url, verifier.references(event))
                self.assertEqual(
                    verifier.regulatory(event)[0]["verification_status"],
                    "REVIEW_REQUIRED",
                )

    def test_capricor_extension_requires_exact_old_and_new_dates(self):
        text = ("Capricor Therapeutics, Inc. announced that the FDA has "
                "extended the PDUFA target action date for Deramiocel "
                "for Duchenne muscular dystrophy (DMD) from "
                "August 22, 2026 to November 22, 2026.")
        proof = self.verifier(text).regulatory(CAPR)[0]
        self.assertEqual(proof["verification_status"], "VERIFIED")
        self.assertEqual(proof["observed"], "2026-11-22")
        self.assertEqual(proof["source_url"], CAPR_URL)
        self.assertTrue(proof["source_sha256"])
        self.assertIn("extension", proof["reason"].lower())

        for wrong in (
            text.replace("November 22, 2026", "December 22, 2026"),
            text.replace("Duchenne muscular dystrophy", "spinal muscular atrophy"),
            text.replace("Deramiocel", "OtherCell"),
            text.replace("Capricor Therapeutics", "Different Sponsor"),
            text.replace("has extended", "might extend"),
        ):
            with self.subTest(wrong=wrong):
                self.assertNotEqual(
                    self.verifier(wrong).regulatory(CAPR)[0]["verification_status"],
                    "VERIFIED",
                )

    def test_bridgebio_goal_date_exact_program_only(self):
        text = ("BridgeBio Pharma, Inc. BBP-418 for limb-girdle muscular "
                "dystrophy type 2I/R9 (LGMD2I/R9). The FDA has assigned a "
                "PDUFA target action date of November 27, 2026.")
        proof = self.verifier(text).regulatory(BBIO)[0]
        self.assertEqual(proof["verification_status"], "VERIFIED")
        self.assertEqual(proof["observed"], "2026-11-27")
        self.assertEqual(proof["source_url"], BBIO_URL)
        self.assertTrue(proof["source_sha256"])

        for wrong in (
            text.replace("November 27, 2026", "December 27, 2026"),
            text.replace("LGMD2I/R9", "ADH1"),
            text.replace("BBP-418", "encaleret"),
            text.replace("BridgeBio Pharma", "Different Sponsor"),
        ):
            with self.subTest(wrong=wrong):
                self.assertNotEqual(
                    self.verifier(wrong).regulatory(BBIO)[0]["verification_status"],
                    "VERIFIED",
                )


if __name__ == "__main__":
    unittest.main()
