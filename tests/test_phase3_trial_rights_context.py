import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from phase3_registry_context import extract_registry_context, validate_registry_context
from phase3_trial_rights_context import build_review
from phase3_sec_rights_documents_pilot import build_report as build_pilot
from test_phase3_sec_rights_documents_pilot import mock_sources


class TrialRightsContextTests(unittest.TestCase):
    def setUp(self):
        self.casebook, self.leads = mock_sources()
        self.registry = {
            "census_total": 741, "source_identity_verified": 741,
            "source_errors": [], "qualified_pipeline_total": None,
            "original_source_records": [],
        }
        for i, row in enumerate(self.casebook["items"]):
            company = f"Company {row['ticker']}"
            row["saved_census_company"] = company
            self.registry["original_source_records"].append({
                "nct_id": row["nct_id"], "source": row["original_registry_api_url"],
                "source_sha256": row["original_registry_sha256"],
                "census_ticker": row["ticker"], "census_company": company,
                "verified_current_commercial_development_rights": False,
                "qualified_pipeline": None,
                "registered_interventions": ([{"name": "Drug Alpha", "type": "DRUG"}] if i % 3 else []),
                "registered_conditions": (["Condition Beta"] if i % 5 else []),
                "registered_context_status": "PARTIAL_OR_NOT_REPORTED" if i % 3 == 0 or i % 5 == 0 else "AVAILABLE",
            })
        self.pilot = build_pilot(
            self.casebook, self.leads,
            fetch=lambda url: b"<html>Company has an exclusive license for an unrelated product.</html>",
            max_issuers=2,
        )

    def report(self):
        return build_review(self.registry, self.casebook, self.leads, self.pilot)

    def test_complete_counts_and_unverified_rights(self):
        result = self.report()
        self.assertEqual(result["total_trials"], 741)
        self.assertEqual(result["total_issuer_pointers"], 130)
        self.assertEqual(result["independently_verified_current_rights"], 0)
        self.assertEqual(result["rights_needing_independent_document_review"], 741)
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertTrue(all(r["qualified_pipeline"] is None and
                            r["independently_verified_current_rights"] is False
                            for r in result["items"]))
        self.assertGreater(result["interventions_reported_trials"], 0)
        self.assertGreater(result["conditions_reported_trials"], 0)

    def test_exact_registered_context_per_trial_no_issuer_copying(self):
        report = self.report()
        self.assertEqual(report["items"][0]["registered_interventions"], [])
        self.assertEqual(report["items"][1]["registered_interventions"][0]["name"], "Drug Alpha")
        self.assertEqual(report["items"][0]["registered_conditions"], [])
        self.assertEqual(report["items"][1]["registered_conditions"], ["Condition Beta"])
        self.assertEqual(report["items"][0]["trial_specific_sec_drug_match"], "NOT_REVIEWED")

    def test_sec_issuer_document_retrieval_does_not_imply_trial_rights(self):
        report = self.report()
        self.assertGreater(report["trials_with_retrieved_issuer_primary_documents"], 0)
        self.assertEqual(report["independently_verified_current_rights"], 0)
        row = report["items"][0]
        self.assertEqual(row["territorial_development_rights"], "NOT_VERIFIED")
        self.assertEqual(row["license_effective_termination_dates"], "NOT_VERIFIED")

    def test_missing_registry_intervention_context_fails_closed(self):
        del self.registry["original_source_records"][0]["registered_interventions"]
        with self.assertRaises(ValueError):
            self.report()

    def test_mismatched_registry_hash_fails_closed(self):
        self.registry["original_source_records"][0]["source_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.report()

    def test_wrong_registered_issuer_company_fails_closed(self):
        self.registry["original_source_records"][0]["census_company"] = "Another company"
        with self.assertRaises(ValueError):
            self.report()

    def test_forged_primary_document_promotion_fails_closed(self):
        self.pilot["issuers"][0]["documents"][0]["verified_trial_development_rights"] = True
        with self.assertRaises(ValueError):
            self.report()

    def test_duplicate_registry_trial_fails_closed(self):
        self.registry["original_source_records"][0]["nct_id"] = self.registry["original_source_records"][1]["nct_id"]
        with self.assertRaises(ValueError):
            self.report()

    def test_invalid_intervention_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            extract_registry_context({"armsInterventionsModule": {
                "interventions": [{"name": "Drug", "type": "UNKNOWN_FAKE"}]}})
        with self.assertRaises(ValueError):
            extract_registry_context({"conditionsModule": {"conditions": 7}})

    def test_exact_ctgov_intervention_and_condition_extraction(self):
        context = extract_registry_context({
            "armsInterventionsModule": {"interventions": [
                {"name": " XYZ-123 ", "type": "DRUG"},
                {"name": "Placebo", "type": "OTHER"},
            ]},
            "conditionsModule": {"conditions": [" Lung Disease ", "Other condition"]},
        })
        self.assertEqual(context["registered_interventions"][0],
                         {"name": "XYZ-123", "type": "DRUG"})
        self.assertEqual(context["registered_conditions"][0], "Lung Disease")
        self.assertEqual(context["registered_context_status"], "AVAILABLE")
        self.assertEqual(validate_registry_context(context), context)


if __name__ == "__main__":
    unittest.main()
