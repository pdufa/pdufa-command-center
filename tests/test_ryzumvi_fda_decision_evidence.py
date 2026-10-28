"""Guard the exact Oct 16, 2026 RYZUMVI supplement outcome mapping.

This test does not fetch the Internet, authorize trading, or promote historical
PDUFA dates to action dates. Canonical verification must still be rerun.
"""
from pathlib import Path
import csv
import json
import unittest
from datetime import date

from scripts.source_verification import Verifier, company_matches, drug_matches, indication_matches


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


    def test_signed_fda_crosswalk_accepts_both_exact_events_only(self):
        letter = (
            "NDA 217064/S-005\nSUPPLEMENT APPROVAL\n"
            "FamyGen Life Sciences, Inc.\n"
            "Ryzumvi (phentolamine mesylate ophthalmic solution) 0.75%.\n"
            "This Prior Approval sNDA adds a new indication for the treatment "
            "of presbyopia in adults.\nAPPROVAL & LABELING\n"
            "It is approved, effective on the date of this letter.\n"
            "Signature Page 1 of 1\nThis is a representation of an electronic "
            "record that was signed electronically.\n/s/ WILLIAM M BOYD\n"
            "10/16/2026 08:47:12 AM"
        )
        label = (
            "NDA 217064/S-005 RYZUMVI (phentolamine ophthalmic solution) 0.75% "
            "indicated for treatment of presbyopia in adults"
        )
        for ticker, event_key in EVENTS.items():
            with self.subTest(ticker=ticker):
                event = next(r for r in self.candidates if r["event_key"] == event_key)
                mapping = self.mappings[ticker]["events"][event_key]
                issuer_text = (
                    event["company"] + " announces that the FDA has approved "
                    "phentolamine ophthalmic solution 0.75% for presbyopia"
                )
                verifier = Verifier([], as_of=date(2026, 10, 25),
                                    issuer_sources=self.mappings)
                def document(url):
                    if url == FDA_LETTER:
                        return b"fda-letter", letter
                    if url == FDA_LABEL:
                        return b"fda-label", label
                    if url == mapping["fda_issuer_approval_url"]:
                        return b"issuer-approval", issuer_text
                    return b"unrelated", "Unrelated filing with no FDA decision"
                verifier.document = document
                # The signed-letter path also hashes the approved label's
                # original bytes. Stub that boundary as well as extraction;
                # this synthetic regression must never fetch a live FDA URL.
                verifier.fetcher = lambda url: document(url)[0]
                self.assertTrue(company_matches({"company": "FamyGen Life Sciences, Inc."}, letter))
                self.assertTrue(company_matches(event, issuer_text), ticker)
                self.assertTrue(drug_matches(event, issuer_text), ticker)
                self.assertTrue(indication_matches(event, issuer_text), ticker)
                self.assertEqual(verifier.primary(event, mapping["fda_issuer_approval_url"]), "ISSUER")
                self.assertEqual(
                    verifier.mapped_fda_action_applicant(
                        event, FDA_LETTER, letter, FDA_LABEL),
                    "FamyGen Life Sciences, Inc."
                )
                outcome = verifier.regulatory(event)[0]
                self.assertEqual(outcome["claim"], "FDA_DECISION", outcome)
                self.assertEqual(outcome["verification_status"], "VERIFIED", outcome)
                self.assertEqual(outcome["observed"], "APPROVED 2026-10-16", outcome)
                self.assertEqual(event["pdufa_date"], "2026-10-17")
                self.assertEqual(event["monitor_eligibility"], "REVIEW")

    def test_fda_crosswalk_rejects_wrong_application_holder_and_unrelated_issuer(self):
        event = next(row for row in self.candidates if row["event_key"] == EVENTS["IRD"])
        letter = (
            "NDA 217064/S-005 SUPPLEMENT APPROVAL FamyGen Life Sciences Inc. "
            "Ryzumvi phentolamine solution for presbyopia."
        )
        approved = (
            "Opus Genetics Inc. announces FDA has approved phentolamine "
            "ophthalmic solution for presbyopia"
        )
        original = self.mappings["IRD"]["events"][EVENTS["IRD"]]
        def verifier_with(mapping, release=approved):
            config = json.loads(json.dumps(self.mappings))
            config["IRD"]["events"][EVENTS["IRD"]] = mapping
            v = Verifier([], as_of=date(2026, 10, 25), issuer_sources=config)
            v.document = lambda url: (b"issuer", release)
            return v
        for changed in (
            {**original, "fda_application_number": "217065"},
            {**original, "fda_supplement_number": "004"},
            {**original, "fda_regulatory_applicant": "Other Applicant LLC"},
            {**original, "fda_issuer_approval_url": "https://untrusted.example/approve"},
            {**original, "approval_label_url": ""},
        ):
            with self.subTest(changed=changed):
                v = verifier_with(changed)
                self.assertEqual(
                    v.mapped_fda_action_applicant(event, FDA_LETTER, letter, FDA_LABEL), "")
        v = verifier_with(original, "Unrelated company announced unrelated approval")
        self.assertEqual(
            v.mapped_fda_action_applicant(event, FDA_LETTER, letter, FDA_LABEL), "")


if __name__ == "__main__":
    unittest.main()
