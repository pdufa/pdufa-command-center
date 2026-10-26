import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_sec_trial_rights_join import build_join
from phase3_sec_rights_documents_pilot import build_report as build_pilot
from test_phase3_sec_rights_documents_pilot import mock_sources


class TrialSecRightsJoinTests(unittest.TestCase):
    def setUp(self):
        self.casebook, self.leads = mock_sources()
        self.pilot = build_pilot(
            self.casebook, self.leads,
            fetch=lambda url: b"<html>License and development rights for unrelated asset</html>",
            max_issuers=2,
        )
        self.program = {
            "report_type": "MAIN_PHASE3_ORIGINAL_DRUG_INDICATION_TERMS_RESEARCH_ONLY",
            "total_trials": 741, "total_saved_issuer_pointers": 130,
            "independently_verified_program_identities": 0,
            "independently_verified_commercial_rights": 0,
            "qualified_pipeline_total": None, "items": [],
        }
        for i, item in enumerate(self.casebook["items"]):
            control = i % 3 == 0
            interventions = ([{"type": "DRUG", "name": "Placebo"}] if control else
                             [{"type": "DRUG", "name": "Drug Alpha"}])
            self.program["items"].append({
                "nct_id": item["nct_id"], "ticker": item["ticker"],
                "original_registry_source_url": item["original_registry_api_url"],
                "original_registry_source_sha256": item["original_registry_sha256"],
                "original_registry_study_title": "Study of an investigational intervention",
                "registry_conditions": ["Disease Beta"],
                "conditions_field_status": "PRESENT",
                "registry_interventions": interventions,
                "interventions_field_status": "PRESENT",
                "provisional_drug_or_biologic_names": [] if control else ["Drug Alpha"],
                "drug_indication_qualified": False,
                "commercial_rights_verified": False,
                "qualified_pipeline": None,
                "identity_review_status": "REGISTRY_TERMS_REQUIRE_INDEPENDENT_REVIEW",
            })

    def result(self):
        return build_join(self.program, self.casebook, self.leads, self.pilot)

    def test_741_130_and_source_denominators(self):
        result = self.result()
        self.assertEqual((result["total_trials"], result["total_issuers"]), (741, 130))
        self.assertEqual(result["trials_with_registered_conditions"], 741)
        self.assertEqual(result["trials_with_issuer_filing_leads"], 741)
        self.assertGreater(result["trials_with_registry_provisional_drugs"], 0)
        self.assertIsNone(result["qualified_pipeline_total"])

    def test_fetched_issuer_document_never_promotes_trial_legal_rights(self):
        result = self.result()
        self.assertGreater(result["trials_with_issuer_primary_document_sources"], 0)
        self.assertEqual(result["verified_current_commercial_rights"], 0)
        self.assertTrue(all(item["current_rights_verified"] is False
                            and item["qualified_pipeline"] is None
                            and item["trial_drug_sec_document_match"] == "NOT_REVIEWED"
                            for item in result["items"]))

    def test_trial_specific_context_is_not_copied_from_issuer(self):
        r = self.result()["items"]
        self.assertEqual(r[0]["provisional_drug_or_biologic_names"], [])
        self.assertEqual(r[1]["provisional_drug_or_biologic_names"], ["Drug Alpha"])
        self.assertEqual(r[0]["registered_interventions"][0]["name"], "Placebo")

    def test_mismatched_original_hash_rejected(self):
        self.program["items"][0]["original_registry_source_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.result()

    def test_claimed_drug_or_rights_qualification_rejected(self):
        self.program["items"][0]["commercial_rights_verified"] = True
        with self.assertRaises(ValueError):
            self.result()

    def test_provisional_name_not_in_registered_interventions_rejected(self):
        self.program["items"][0]["provisional_drug_or_biologic_names"] = ["Invented drug"]
        with self.assertRaises(ValueError):
            self.result()

    def test_unknown_pilot_document_url_rejected(self):
        self.pilot["issuers"][0]["documents"][0]["sec_primary_document_url"] = "https://example.org/not-sec"
        with self.assertRaises(ValueError):
            self.result()

    def test_forged_sec_digest_rejected(self):
        self.pilot["issuers"][0]["documents"][0]["source_sha256"] = "not-a-hash"
        with self.assertRaises(ValueError):
            self.result()

    def test_duplicate_trial_rejected(self):
        self.program["items"][1]["nct_id"] = self.program["items"][0]["nct_id"]
        with self.assertRaises(ValueError):
            self.result()


if __name__ == "__main__":
    unittest.main()
