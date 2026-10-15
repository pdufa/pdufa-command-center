"""FDA original BLA approval: proof must be a matching signed FDA letter."""
import json
import unittest
from datetime import date
from pathlib import Path

from scripts.source_verification import (
    Verifier, documented_fda_signed_original_bla_approval,
)

ROOT = Path(__file__).resolve().parents[1]
KEY = "SRRK|APITEGROMAB_20260930"
URL = ("https://www.accessdata.fda.gov/drugsatfda_docs/appletter/"
       "2026/761463Orig1s000ltr.pdf")
COMPANY = {"ticker": "SRRK", "company": "Scholar Rock Holding Corp",
           "cik10": "0001727196"}
EVENT = {
    "event_key": KEY, "ticker": "SRRK",
    "company": COMPANY["company"],
    "drug": "apitegromab",
    "indication": "spinal muscular atrophy; age >=2 on SMN2-targeted treatment",
    "pdufa_date": "2026-09-30",
    "decision_date": "2026-09-11", "outcome": "APPROVED",
}

# Mimic the distinctive exact statements in FDA's 2026 BLA 761463 letter,
# including the original authorization and FDA electronic-signature page.
SIGNED = """
BLA 761463
BLA APPROVAL
Scholar Rock, Inc.
Please refer to your biologics license application (BLA) under 351(a)
for Isembyld (apitegromab-mstn) injection.
LICENSING
We are issuing Department of Health and Human Services U.S. License
No. 2372 to Scholar Rock, Inc.
The license authorizes you to introduce or deliver for introduction
into interstate commerce the licensed product.
Under this license, you are authorized to manufacture Isembyld
(apitegromab-mstn). Isembyld is indicated for the treatment of
spinal muscular atrophy (SMA) in adults and pediatric patients
2 years of age and older who are currently receiving a
survival motor neuron 2 (SMN2)-targeted treatment.
MANUFACTURING LOCATIONS
Production and packaging requirements.
APPROVAL & LABELING
We have completed our review of this application.
It is approved, effective on the date of this letter.
Signature Page 1 of 1
This is a representation of an electronic record that was signed
electronically. Following this are manifestations of electronic signatures.
09/11/2026 04:42:12 PM
"""


class SignedOriginalBlaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT / "config/issuer_sources.json").read_text())

    def verifier(self, doc):
        return Verifier([COMPANY], issuer_sources=self.config,
                        fetch=lambda url: doc.encode("utf-8"),
                        as_of=date(2026, 10, 14))

    def test_exact_source_discovery_is_not_a_preverified_result(self):
        source = self.config["SRRK"]["events"][KEY]
        self.assertEqual(source["urls"], [URL])
        for invalid in ("verified", "decision_status", "entry_ready", "approval"):
            self.assertNotIn(invalid, source)
        self.assertEqual(self.verifier("noise").primary(EVENT, URL), "FDA")
        self.assertEqual(
            self.verifier("noise").regulatory(EVENT)[0]["verification_status"],
            "REVIEW_REQUIRED")

    def test_matching_original_bla_is_verified_with_signed_date(self):
        self.assertEqual(
            documented_fda_signed_original_bla_approval(EVENT, URL, SIGNED),
            "2026-09-11")
        out = self.verifier(SIGNED).regulatory(EVENT)[0]
        self.assertEqual(out["verification_status"], "VERIFIED", out)
        self.assertEqual(out["claim"], "FDA_DECISION")
        self.assertEqual(out["observed"], "APPROVED 2026-09-11")
        self.assertEqual(out["source_url"], URL)
        self.assertEqual(len(out["source_sha256"]), 64)
        self.assertNotIn("entry_ready", out)

    def test_wrong_event_date_requires_conflict_not_false_approval(self):
        altered = {**EVENT, "decision_date": "2026-09-30"}
        self.assertEqual(
            self.verifier(SIGNED).regulatory(altered)[0]["verification_status"],
            "CONFLICT")

    def test_missing_or_wrong_signed_primary_proof_rejected(self):
        cases = [
            (SIGNED.replace("BLA 761463", "BLA 999999"), URL),
            (SIGNED, URL.replace("761463", "111111")),
            (SIGNED.replace("BLA APPROVAL", "BLA UNDER REVIEW"), URL),
            (SIGNED.replace("Scholar Rock, Inc.", "Unrelated Biotech"), URL),
            (SIGNED.replace("apitegromab-mstn", "otherdrug"), URL),
            (SIGNED.replace("spinal muscular atrophy", "unrelated disease"), URL),
            (SIGNED.replace("It is approved", "It might be approved"), URL),
            (SIGNED.replace("Signature Page 1 of 1", "Signature missing"), URL),
            (SIGNED.replace("signed\nelectronically", "unsigned"), URL),
            (SIGNED.replace("09/11/2026 04:42:12 PM", "No digital signing time"), URL),
            (SIGNED.replace("LICENSE", "UNLICENSED"), URL.replace("appletter", "label")),
        ]
        for doc, url in cases:
            with self.subTest(case=doc[-100:], url=url):
                self.assertIsNone(
                    documented_fda_signed_original_bla_approval(EVENT, url, doc))

    def test_old_supplement_approval_logic_still_separate(self):
        # The original-BLA parser cannot qualify an NDA supplement or an
        # uncorroborated issuer claim, even if they mention FDA approval.
        other = URL.replace("761463Orig1s000ltr", "761463Orig1s001ltr")
        self.assertIsNone(
            documented_fda_signed_original_bla_approval(EVENT, other, SIGNED))


if __name__ == "__main__":
    unittest.main()
