"""Exact-event source anchors for imminent IRD and INO FDA target reviews.

The mapped phrase only identifies a claim to verify in newly fetched issuer
content. It is never an FDA outcome or a trade-entry permission.
"""
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.source_verification import Verifier

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/issuer_sources.json"
CASES = (
    (
        "IRD", "IRD|PHENTOLAMINE_PRESBYOPIA_20261017",
        "Opus Genetics, Inc.", "0001228627",
        "phentolamine ophthalmic solution 0.75%", "presbyopia",
        "2026-10-17", "The FDA has assigned a PDUFA goal date of October 17, 2026",
    ),
    (
        "INO", "INO|INO3107_RRP_20261030",
        "INOVIO Pharmaceuticals, Inc.", "0001055726",
        "INO-3107", "recurrent respiratory papillomatosis",
        "2026-10-30",
        "The FDA assigned INO-3107 a Prescription Drug User Fee Act (PDUFA) review goal date of October 30, 2026",
    ),
)


class ExactPrimaryTargetsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def check(self, company, event, plain):
        verifier = Verifier(
            [company], issuer_sources=self.config,
            fetch=lambda url: plain.encode("utf-8"),
            as_of=date(2026, 10, 14),
        )
        return verifier.regulatory(event, _discovery_only=True)[0]

    def test_only_fetched_exact_claim_can_be_verified(self):
        for ticker, key, name, cik, drug, indication, target, anchor in CASES:
            with self.subTest(ticker=ticker):
                company = {"ticker": ticker, "company": name, "cik10": cik}
                event = {"event_key": key, "ticker": ticker, "company": name,
                         "drug": drug, "indication": indication, "pdufa_date": target}
                config = self.config[ticker]["events"][key]
                self.assertEqual(config["primary_target_anchor"], anchor)
                self.assertNotIn("verified", config)
                self.assertNotIn("fda_approval", config)
                issuer_text = f"{name}: {drug} for {indication}. {anchor}."
                outcome = self.check(company, event, issuer_text)
                self.assertEqual(outcome["verification_status"], "VERIFIED")
                self.assertEqual(outcome["observed"], target)
                self.assertEqual(len(outcome["source_sha256"]), 64)
                for bad in (
                    issuer_text.replace(indication, "an unrelated condition"),
                    issuer_text.replace(target[-4:], "2099") if False else issuer_text.replace(
                        anchor, anchor.replace("2026", "2027")
                    ),
                    f"Another issuer: {drug} for {indication}. {anchor}.",
                    f"{name}: {drug} for {indication}, but the actual PDUFA date was not disclosed.",
                ):
                    with self.subTest(ticker=ticker, text=bad[:70]):
                        result = self.check(company, event, bad)
                        self.assertNotEqual(result["verification_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
