"""Trusted synthetic tests for research-only level scaffold."""
import importlib.util
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/continuous_stage_drafts/level_17_intake.py"
SPEC = importlib.util.spec_from_file_location("review_module", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class EvidenceIntakeTests(unittest.TestCase):
    def test_missing_sources_are_not_negative_trial_results(self):
        x = MODULE.assess({"nct": "NCT00000001", "evidence_fields": {}})
        self.assertEqual(len(x["missing_source_fields"]), len(MODULE.REQUIRED_FIELDS))
        self.assertFalse(x["scientific_stage_complete"])
        self.assertFalse(x["source_facts_independently_verified"])
        self.assertIsNone(x["approval_probability"])
        self.assertIsNone(x["fda_prediction"])
    def test_all_keys_are_present_but_science_remains_unverified(self):
        fields = {k: "UNVERIFIED source receipt" for k in MODULE.REQUIRED_FIELDS}
        x = MODULE.assess({"nct": "NCT00000001", "evidence_fields": fields})
        self.assertEqual(x["missing_source_fields"], [])
        self.assertFalse(x["scientific_stage_complete"])
        self.assertIsNone(x["clinical_score"])
    def test_bad_nct_rejected(self):
        for nct in ("NCT1", "NCT١٢٣٤٥٦٧٨", "../NCT00000001"):
            with self.assertRaises(ValueError):
                MODULE.assess({"nct": nct})
    def test_invalid_source_structure_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.assess({"nct": "NCT00000001", "evidence_fields": []})

if __name__ == "__main__":
    unittest.main()
