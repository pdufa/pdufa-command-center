"""Specific company-disclosed rights must not be elevated to independently adjudicated legal rights or PDUFA."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CENSUS = ROOT / "data/phase3_all_years_300m_10b_trials.csv"
CASE = ROOT / "data/research_abvx_obefazimod_rights_2026-10-26.json"

class AbvxRightsDisclosureEvidenceTests(unittest.TestCase):
    def test_three_verified_public_program_links_but_no_independent_legal_confirmation(self):
        item = json.loads(CASE.read_text(encoding="utf-8"))
        self.assertEqual(item["issuer"]["ticker"], "ABVX")
        self.assertEqual(item["issuer"]["cik"], "0001956827")
        trials = set(item["program"]["trialNctIds"])
        self.assertEqual(trials, {"NCT05507203", "NCT05507216", "NCT05535946"})
        import csv
        with CENSUS.open(newline="", encoding="utf-8-sig") as handle:
            census = list(csv.DictReader(handle))
        known = {r["nct_id"] for r in census if r["ticker"] == "ABVX"}
        self.assertTrue(trials.issubset(known))
        findings = item["evidenceFindings"]
        self.assertEqual(findings["trial_linked_rights_claim_count"], 3)
        self.assertTrue(findings["issuer_public_worldwide_rights_claim_documented"])
        self.assertTrue(findings["program_to_three_trial_nct_ids_source_linked"])
        self.assertFalse(findings["rights_contract_terms_independently_validated"])
        self.assertFalse(findings["current_unencumbered_legal_rights_independently_verified"])
        self.assertFalse(findings["official_pdufa_target_date_confirmed"])
        self.assertFalse(findings["fda_nda_acceptance_confirmed"])
        self.assertIsNone(findings["qualified_pipeline"])

    def test_primary_sources_are_explicit_and_issuer_attributed(self):
        item = json.loads(CASE.read_text(encoding="utf-8"))
        sources = item["primarySources"]
        self.assertEqual(len(sources), 4)
        self.assertTrue(any(x["sourceType"] == "SEC_FORM_20_F" and
                            x["claimType"] == "ISSUER_SELF_REPORTED_WORLDWIDE_DEVELOPMENT_AND_COMMERCIALIZATION_RIGHTS" for x in sources))
        self.assertTrue(any(x["claimType"] == "PROGRAM_TO_NCT_ID_MAPPING" for x in sources))
        self.assertTrue(all(x["url"].startswith("https://") for x in sources))


if __name__ == "__main__":
    unittest.main()
