"""Guard the exact Oct 16, 2026 RYZUMVI supplement outcome mapping.

This test does not fetch the Internet, authorize trading, or promote historical
PDUFA dates to action dates. Canonical verification must still be rerun.
"""
from pathlib import Path
import csv
import json
import unittest

from scripts.source_verification import Verifier


ROOT = Path(__file__).resolve().parents[1]
EVENTS = {
    "IRD": "IRD|PHENTOLAMINE_PRESBYOPIA_20261017",
    "VTRS": "VTRS|PHENTOLAMINE_PRESBYOPIA_20261017",
}
FDA_LETTER = (
    "https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/"
    "217064Orig1s005ltr.pdf"
)
FDA_LABEL = (
    "https://www.accessdata.fda.gov/drugsatfda_docs/label/2026/"
    "217064s005lbl.pdf"
)


class RyzumviOutcomeEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (ROOT / "data/pdufa_candidates.csv").open(newline="", encoding="utf-8") as f:
            cls.candidates = list(csv.DictReader(f))
        cls.mappings = json.loads((ROOT / "config/issuer_sources.json").read_text(encoding="utf-8"))

    def test_same_fda_action_preserves_separate_company_ids_and_original_goal(self):
        found = [row for row in self.candidates if row["event_key"] in EVENTS.values()]
        self.assertEqual(len(found), 2)
        self.assertEqual({row["ticker"] for row in found}, set(EVENTS))
        for row in found:
            self.assertEqual(row["event_key"], EVENTS[row["ticker"]])
            self.assertEqual(row["pdufa_date"], "2026-10-17")
            self.assertEqual(row["outcome"], "APPROVED")
            self.assertEqual(row["decision_date"], "2026-10-16")
            self.assertEqual(row["monitor_eligibility"], "REVIEW")
            # This correction does not validate a second financing or trade.
            self.assertNotEqual(row["financing_status"], "TWO_DISTINCT_POST_PHASE3_CLOSES_SOURCE_ATTESTED")

    def test_both_exact_events_have_fda_supplement_letter_and_issuer_proof(self):
        issuer_hosts = {"IRD": "ir.opusgtx.com", "VTRS": "newsroom.viatris.com"}
        for ticker, event_key in EVENTS.items():
            with self.subTest(ticker=ticker):
                conf = self.mappings[ticker]["events"][event_key]
                self.assertEqual(conf["urls"][0], FDA_LETTER)
                self.assertEqual(conf["approval_label_url"], FDA_LABEL)
                self.assertTrue(any(issuer_hosts[ticker] in url and
                                    ("approval" in url.lower() or "fda-approval" in url.lower())
                                    for url in conf["urls"][1:]))
                self.assertTrue(any("accept" in url.lower() for url in conf["urls"][1:]))
                row = next(x for x in self.candidates if x["event_key"] == event_key)
                verifier = Verifier([], issuer_sources=self.mappings)
                self.assertIn(FDA_LETTER, verifier.references(row))
                self.assertEqual(verifier.primary(row, FDA_LETTER), "FDA")
                self.assertEqual(verifier.primary(row, conf["urls"][1]), "ISSUER")


if __name__ == "__main__":
    unittest.main()
