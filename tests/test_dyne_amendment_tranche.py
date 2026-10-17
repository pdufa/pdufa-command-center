"""Regression: exact dated SEC debt tranche is funded, facility limit is not."""
from datetime import date
import unittest

from scripts.source_verification import Verifier, documented_drawn_credit_tranche

EVENT_KEY = "DYN|ZROSTUDIRSEN_DMD_20270121"
SOURCE = "https://www.sec.gov/Archives/edgar/data/1818794/000181879426000003/dyn-20260616.htm"
TEXT = (
    "On June 16, 2026 (the “Amendment Closing Date”), "
    "Dyne Therapeutics, Inc. (the “Company”) entered into the Second Amendment "
    "to its Loan and Security Agreement with Hercules Capital, Inc. "
    "The amendment expanded the debt facility to an aggregate of up to "
    "$400.0 million. Pursuant to the Second Amendment, the Company borrowed "
    "one of the additional loan tranches in an aggregate principal amount "
    "of $50.0 million on the Amendment Closing Date. Three additional "
    "tranches remain subject to milestones and approval."
)

class DyneTrancheTests(unittest.TestCase):
    def test_actual_borrowing_only_not_facility_limit(self):
        excerpt = documented_drawn_credit_tranche(TEXT, "2026-06-16")
        self.assertIn("$50.0 million", excerpt)
        self.assertNotIn("three additional tranches", excerpt.lower())
        self.assertFalse(documented_drawn_credit_tranche(TEXT, "2026-06-17"))
        future = TEXT.replace("the Company borrowed one", "the Company may borrow one")
        self.assertFalse(documented_drawn_credit_tranche(future, "2026-06-16"))
        no_borrow = TEXT.split("Pursuant to the Second Amendment")[0]
        self.assertFalse(documented_drawn_credit_tranche(no_borrow, "2026-06-16"))

    def test_exact_sec_claim_not_second_financing_gate(self):
        registry = [{"ticker":"DYN","cik10":"0001818794","company":"Dyne Therapeutics, Inc."}]
        sources = {"DYN":{"events":{EVENT_KEY:{"individual_financing_close":{
            "date":"2026-06-16","sec_url":SOURCE,
        }}}}}
        event = {"ticker":"DYN","event_key":EVENT_KEY,
                 "company":"Dyne Therapeutics, Inc.","financing_close_date":"",
                 "financing_evidence_url":""}
        verifier = Verifier(registry, fetch=lambda url: TEXT.encode(),
                            as_of=date(2026,10,17), issuer_sources=sources)
        result = verifier.financing(event)
        self.assertEqual(result["verification_status"], "VERIFIED", result)
        self.assertIn("not the post-Phase-3 second-financing sequence", result["reason"])
        self.assertEqual(result["observed"], "2026-06-16")
        self.assertTrue(result["source_sha256"])
        other = dict(event, event_key="DYN|OTHER_DRUG_EVENT")
        self.assertEqual(verifier.financing(other)["verification_status"], "REVIEW_REQUIRED")

if __name__ == "__main__":
    unittest.main()
