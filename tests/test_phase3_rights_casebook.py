import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_qualification_ledger import GATES
from phase3_rights_casebook import build_casebook


class RightsCasebookTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "qualified_pipeline_total": None, "records": []}
        self.registry = {"census_total": 741, "source_identity_verified": 741,
                         "source_errors": [], "qualified_pipeline_total": None,
                         "original_source_records": []}
        self.sponsor = {"total": 741, "review_required": 741,
                        "qualified_pipeline_total": None, "items": []}
        self.gaps = {"trial_count": 741, "issuer_count": 130,
                     "independently_verified_current_development_rights": 0,
                     "qualified_pipeline_count": None, "trials": []}
        for i in range(1, 742):
            nct = f"NCT{i:08d}"
            ticker = f"T{i % 130:03d}"
            company = f"Company {i % 130}"
            cik = f"{i % 130 + 1:010d}"
            url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
            study = f"https://clinicaltrials.gov/study/{nct}"
            digest = "a" * 64
            self.ledger["records"].append({
                "nct_id": nct, "ticker": ticker, "company": company,
                "source_url": study, "source_sha256": digest,
                "qualified_pipeline": None, "gates": {
                    g: "PASS" if g == "registry_identity" else "REVIEW" for g in GATES}})
            self.registry["original_source_records"].append({
                "nct_id": nct, "census_ticker": ticker, "census_company": company,
                "source": url, "source_sha256": digest,
                "currently_registered_lead_sponsor": company})
            self.sponsor["items"].append({
                "nct_id": nct, "ticker": ticker, "census_company": company,
                "original_registry_url": url, "source_sha256": digest,
                "registered_lead_sponsor": company,
                "review_gate": "current_commercial_rights", "review_status": "REVIEW",
                "commercial_rights_verified": False})
            self.gaps["trials"].append({
                "nct_id": nct, "ticker": ticker,
                "registry_lead_sponsor_name": company, "registry_record_url": study,
                "issuer_cik": cik,
                "issuer_sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
                "current_development_rights_status": "RIGHTS_NOT_ESTABLISHED",
                "current_rights_primary_source": None, "qualified_pipeline": None})

    def run_build(self):
        return build_casebook(self.ledger, self.registry, self.sponsor, self.gaps)

    def test_complete_741_130_casebook_without_rights_promotion(self):
        result = self.run_build()
        self.assertEqual((result["total_trials"], result["saved_issuer_pointers"]), (741, 130))
        self.assertEqual(result["registry_sponsor_comparisons"]["MATCH"], 741)
        self.assertEqual((result["rights_verified_trials"], result["rights_unverified_trials"]), (0, 741))
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertTrue(all(x["independent_rights_source_url"] is None and
                            x["qualified_pipeline"] is None for x in result["items"]))

    def test_changed_current_sponsor_is_review_not_verified(self):
        self.registry["original_source_records"][0]["currently_registered_lead_sponsor"] = "New sponsor"
        self.sponsor["items"][0]["registered_lead_sponsor"] = "New sponsor"
        result = self.run_build()
        self.assertEqual(result["registry_sponsor_comparisons"]["MISMATCH_REVIEW"], 1)
        self.assertEqual(result["rights_verified_trials"], 0)

    def test_missing_trial_fails_closed(self):
        self.gaps["trials"].pop()
        with self.assertRaises(ValueError):
            self.run_build()

    def test_wrong_sec_cik_fails_closed(self):
        self.gaps["trials"][0]["issuer_sec_submissions_url"] = "https://fake.example/CIK123.json"
        with self.assertRaises(ValueError):
            self.run_build()

    def test_claimed_rights_fails_closed(self):
        self.gaps["trials"][0]["current_development_rights_status"] = "VERIFIED_RIGHTS"
        with self.assertRaises(ValueError):
            self.run_build()

    def test_source_digest_mismatch_fails_closed(self):
        self.registry["original_source_records"][0]["source_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.run_build()

    def test_conflicting_same_ticker_issuer_fails_closed(self):
        self.gaps["trials"][130]["issuer_cik"] = "0000012345"
        self.gaps["trials"][130]["issuer_sec_submissions_url"] = "https://data.sec.gov/submissions/CIK0000012345.json"
        with self.assertRaises(ValueError):
            self.run_build()

    def test_registry_retrieval_error_fails_closed(self):
        self.registry["source_errors"] = [{"nct_id": "NCT00000001"}]
        with self.assertRaises(ValueError):
            self.run_build()


if __name__ == "__main__":
    unittest.main()
