import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_phase3_original_registry_pilot import extract_original_study, original_program_field
from phase3_trial_program_identity import build_report


class ProgramOriginalFieldsTests(unittest.TestCase):
    def setUp(self):
        self.expected = {"nct_id": "NCT12345678", "status": "RECRUITING",
                         "ticker": "TEST", "company": "Trial Sponsor"}
        self.payload = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678",
                                     "briefTitle": "Drug A in Disease B"},
            "statusModule": {"overallStatus": "RECRUITING"},
            "designModule": {"phases": ["PHASE3"]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Trial Sponsor"}},
            "conditionsModule": {"conditions": ["Disease B"]},
            "armsInterventionsModule": {"interventions": [
                {"type": "DRUG", "name": "Drug A"},
                {"type": "DRUG", "name": "Placebo"},
            ]},
        }}

    def source(self):
        return extract_original_study(json.dumps(self.payload).encode(),
                                      self.expected, "2026-10-26T00:00:00Z")

    def test_original_named_intervention_and_indication_provenance(self):
        record = self.source()
        self.assertEqual(record["registry_study_title"], "Drug A in Disease B")
        self.assertEqual(record["registry_condition_names"], ["Disease B"])
        self.assertEqual(record["registry_interventions"][0], {"type": "DRUG", "name": "Drug A"})
        self.assertEqual(record["registry_conditions_field_status"], "PRESENT")
        self.assertEqual(record["registry_interventions_source_count"], 2)
        self.assertIsNone(record["qualified_pipeline"])
        self.assertFalse(record["verified_current_commercial_development_rights"])

    def test_missing_source_program_fields_not_treated_as_known_none(self):
        self.payload["protocolSection"].pop("conditionsModule")
        self.payload["protocolSection"].pop("armsInterventionsModule")
        source = self.source()
        self.assertEqual(source["registry_conditions_field_status"], "SECTION_MISSING")
        self.assertEqual(source["registry_interventions_field_status"], "SECTION_MISSING")
        self.assertEqual(source["registry_condition_names"], [])

    def test_malformed_and_overlimit_are_review_not_silent_empty(self):
        self.payload["protocolSection"]["armsInterventionsModule"]["interventions"] = ["bad shape"]
        self.assertEqual(self.source()["registry_interventions_field_status"], "ITEM_INVALID")
        self.payload["protocolSection"]["armsInterventionsModule"]["interventions"] = [
            {"type": "DRUG", "name": "D"} for _ in range(101)]
        source = self.source()
        self.assertEqual(source["registry_interventions_field_status"], "OVER_LIMIT_REVIEW")
        self.assertEqual(source["registry_interventions_source_count"], 101)
        self.assertEqual(source["registry_interventions"], [])


class FullProgramIdentityTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"census_total": 741, "source_identity_verified": 741,
                         "source_errors": [], "qualified_pipeline_total": None,
                         "original_source_records": []}
        self.casebook = {"report_type": "MAIN_PHASE3_RIGHTS_CASEBOOK_RESEARCH_ONLY",
                         "total_trials": 741, "saved_issuer_pointers": 130,
                         "rights_verified_trials": 0, "rights_unverified_trials": 741,
                         "qualified_pipeline_total": None, "items": []}
        for i in range(1, 742):
            nct = f"NCT{i:08d}"
            ticker = f"T{i % 130:03d}"
            original_url = f"https://clinicaltrials.gov/api/v2/studies/{nct}"
            self.registry["original_source_records"].append({
                "nct_id": nct, "census_ticker": ticker,
                "census_company": "Sponsor",
                "source": original_url, "source_sha256": "a" * 64,
                "registry_study_title": "Drug A for Condition B",
                "registry_condition_names": ["Condition B"],
                "registry_conditions_field_status": "PRESENT",
                "registry_conditions_source_count": 1,
                "registry_interventions": [{"name": "Drug A", "type": "DRUG"},
                                           {"name": "Placebo", "type": "DRUG"}],
                "registry_interventions_field_status": "PRESENT",
                "registry_interventions_source_count": 2,
            })
            self.casebook["items"].append({
                "nct_id": nct, "ticker": ticker, "saved_census_company": "Sponsor",
                "original_registry_api_url": original_url,
                "original_registry_sha256": "a" * 64,
                "rights_verification_status": "NOT_ESTABLISHED",
                "qualified_pipeline": None,
            })

    def build(self):
        return build_report(self.registry, self.casebook)

    def test_741_nct_130_ticker_denominators_and_no_rights(self):
        report = self.build()
        self.assertEqual((report["total_trials"], report["total_saved_issuer_pointers"]), (741, 130))
        self.assertEqual(report["trials_with_named_conditions"], 741)
        self.assertEqual(report["trials_with_named_interventions"], 741)
        self.assertEqual(report["trials_with_provisional_drug_or_biologic_mentions"], 741)
        self.assertEqual(report["independently_verified_program_identities"], 0)
        self.assertEqual(report["independently_verified_commercial_rights"], 0)
        self.assertIsNone(report["qualified_pipeline_total"])
        self.assertEqual(report["items"][0]["provisional_drug_or_biologic_names"], ["Drug A"])

    def test_biologic_control_filter_and_no_drug_is_not_negative_proof(self):
        record = self.registry["original_source_records"][0]
        record["registry_interventions"] = [
            {"type": "DRUG", "name": "Saline"},
            {"type": "BIOLOGICAL", "name": "Protein X"}]
        self.assertEqual(self.build()["items"][0]["provisional_drug_or_biologic_names"], ["Protein X"])
        record["registry_interventions"] = [
            {"type": "DRUG", "name": "Placebo"},
            {"type": "PROCEDURE", "name": "Surgery"}]
        report = self.build()
        self.assertEqual(report["trials_without_provisional_drug_or_biologic_mentions"], 1)
        self.assertEqual(report["independently_verified_program_identities"], 0)

    def test_missing_registry_fields_count_as_review_not_qualification(self):
        record = self.registry["original_source_records"][0]
        record["registry_interventions"] = []
        record["registry_interventions_source_count"] = 0
        record["registry_interventions_field_status"] = "SECTION_MISSING"
        report = self.build()
        self.assertEqual(report["trials_with_missing_or_invalid_original_program_fields"], 1)
        self.assertFalse(report["items"][0]["commercial_rights_verified"])

    def test_duplicate_nct_rejected(self):
        self.registry["original_source_records"][0]["nct_id"] = self.registry["original_source_records"][1]["nct_id"]
        with self.assertRaises(ValueError):
            self.build()

    def test_source_hash_mismatch_rejected(self):
        self.registry["original_source_records"][0]["source_sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.build()

    def test_forged_named_count_rejected(self):
        self.registry["original_source_records"][0]["registry_interventions_source_count"] = 500
        with self.assertRaises(ValueError):
            self.build()

    def test_missing_original_fields_rejected_not_assumed_empty(self):
        self.registry["original_source_records"][0].pop("registry_interventions")
        with self.assertRaises(ValueError):
            self.build()

    def test_unsafe_qualification_claim_rejected(self):
        self.casebook["items"][0]["rights_verification_status"] = "VERIFIED"
        with self.assertRaises(ValueError):
            self.build()


if __name__ == "__main__":
    unittest.main()
