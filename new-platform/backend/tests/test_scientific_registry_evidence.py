"""Tests for descriptive ClinicalTrials.gov evidence extraction."""
import unittest
from app.scientific_registry_evidence import extract_trial_evidence


class ScientificRegistryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "designModule": {
                "designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "DOUBLE"}},
                "enrollmentInfo": {"count": 250},
            },
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
            "statusModule": {"overallStatus": "COMPLETED"},
        }}

    def test_source_metadata_preserved_without_scoring(self):
        result = extract_trial_evidence("NCT12345678", self.record)
        self.assertEqual(result["nctId"], "NCT12345678")
        self.assertEqual(result["sourceUrl"], "https://clinicaltrials.gov/study/NCT12345678")
        self.assertEqual(result["metadata"]["allocation"], "RANDOMIZED")
        self.assertEqual(result["metadata"]["enrollment"], 250)
        self.assertEqual(result["metadata"]["primaryOutcomes"][0]["measure"], "Overall survival")
        self.assertEqual(result["scoringEvidence"], {})
        self.assertEqual(result["verificationStatus"], "source_record_only")

    def test_identity_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            extract_trial_evidence("NCT87654321", self.record)

    def test_invalid_identity_rejected(self):
        with self.assertRaises(ValueError):
            extract_trial_evidence("TRIAL|NCT12345678", self.record)

    def test_absent_design_fields_remain_missing(self):
        result = extract_trial_evidence("NCT12345678", {
            "protocolSection": {"identificationModule": {"nctId": "NCT12345678"}}
        })
        self.assertIsNone(result["metadata"]["allocation"])
        self.assertEqual(result["metadata"]["primaryOutcomes"], [])
        self.assertEqual(result["scoringEvidence"], {})


if __name__ == "__main__":
    unittest.main()
