"""Level 4 original-source scientific evidence review gates (offline, synthetic)."""
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("level4_review", ROOT / "scripts/level4_scientific_evidence.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
NCT = "NCT05507203"
URL = "https://clinicaltrials.gov/api/v2/studies/" + NCT

def fixture():
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT},
            "statusModule": {"lastUpdatePostDateStruct": {"date": "2026-09-01"}},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"],
                "designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "DOUBLE"}}},
            "outcomesModule": {"primaryOutcomes": [
                {"measure": "Primary score", "timeFrame": "Week 12"},
                {"measure": "Remission", "timeFrame": "Week 12"}]},
        },
        "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [
            {"type": "PRIMARY", "measure": "Primary score", "timeFrame": "Week 12",
             "analyses": [{"pValue": "0.02"}]},
            {"type": "SECONDARY", "measure": "Remission", "timeFrame": "Week 12"}]}},
        "documentSection": {"largeDocumentModule": {"largeDocs": [{"type": "SAP"}]}}
    }
    receipt = {"nct": NCT, "source_url": URL,
               "sha256": "f" * 64, "retrieved_at_utc": "2026-11-12T13:00:00Z"}
    return record, receipt

class Level4EvidenceTests(unittest.TestCase):
    def test_source_receipt_and_primary_endpoints_inventory(self):
        record, receipt = fixture()
        out = M.summarize(record, receipt)
        self.assertTrue(out["original_source_retrieved"])
        self.assertEqual(out["observed_registry_fields"]["registered_primary_endpoints"], 2)
        self.assertEqual(out["observed_registry_fields"]["posted_primary_outcome_records"], 1)
        self.assertEqual(out["observed_registry_fields"]["possible_textual_primary_endpoint_matches"], 1)
        self.assertEqual(out["source"]["raw_sha256"], "f" * 64)
        self.assertEqual(out["observed_registry_fields"]["phases"], ["PHASE3"])
        self.assertIn("multiplicity_control_independent_review", out["missing_or_unverified"])

    def test_no_scientific_pass_from_synthetic_pvalue(self):
        record, receipt = fixture()
        out = M.summarize(record, receipt)
        self.assertFalse(out["scientific_stage_complete"])
        self.assertFalse(out["source_facts_independently_verified"])
        self.assertEqual(out["independent_review"], "REQUIRED")
        self.assertIsNone(out["fda_prediction"])
        self.assertIsNone(out["approval_probability"])
        self.assertIsNone(out["clinical_score"])

    def test_record_without_results_is_gap_not_failure(self):
        record, receipt = fixture()
        del record["resultsSection"]
        del record["documentSection"]
        report = M.summarize(record, receipt)
        self.assertFalse(report["observed_registry_fields"]["registry_results_section_present"])
        self.assertIn("primary_result_statistics", report["missing_or_unverified"])
        self.assertIn("statistical_analysis_plan_document", report["missing_or_unverified"])
        self.assertFalse(report["scientific_stage_complete"])

    def test_exact_identity_and_valid_receipt_required(self):
        record, receipt = fixture()
        with self.assertRaises(ValueError):
            M.retrieve_and_summarize("NCT٠٥٥٠٧٢٠٣", fetcher=lambda n: (record, receipt))
        record["protocolSection"]["identificationModule"]["nctId"] = "NCT00000000"
        with self.assertRaises(ValueError):
            M.summarize(record, receipt)
        record["protocolSection"]["identificationModule"]["nctId"] = NCT
        receipt["sha256"] = "garbage"
        with self.assertRaises(ValueError):
            M.summarize(record, receipt)

    def test_batch_retries_per_trial_without_affecting_others(self):
        record, receipt = fixture()
        def retrieve(nct):
            if nct == NCT:
                return record, receipt
            raise TimeoutError("original registry unavailable")
        batch = M.process_ncts([NCT, "NCT00000002"], fetcher=retrieve)
        self.assertEqual(batch["retrieved"], 1)
        self.assertEqual(batch["reports"][1]["status"], "SOURCE_RETRIEVAL_OR_VALIDATION_BLOCKED")
        self.assertFalse(batch["scientific_level_complete"])
        with self.assertRaises(ValueError):
            M.process_ncts([NCT, NCT], fetcher=retrieve)

    def test_metadata_not_treated_as_blind_historical_source(self):
        record, receipt = fixture()
        out = M.summarize(record, receipt, as_of="2026-05-01")
        self.assertEqual(out["source"]["source_revision"], "CURRENT_STATE_NOT_HISTORICAL_FREEZE")
        self.assertEqual(out["source"]["requested_as_of"], "2026-05-01")
        self.assertFalse(out["scientific_stage_complete"])

if __name__ == "__main__":
    unittest.main()
