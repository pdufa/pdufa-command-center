"""Synthetic evidence metadata validation; no real clinical source assertions."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "scripts/continuous_provenance/level_15_provenance.py"
SPEC = importlib.util.spec_from_file_location("level_provenance", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def record():
    return {"nct": "NCT00000001", "trial_phase": 2,
            "knowledge_cutoff": "2026-01-01", "source_metadata": {}}


class ProvenanceGateTests(unittest.TestCase):
    def test_missing_evidence_does_not_imply_trial_failure(self):
        result = MODULE.inspect_metadata(record())
        self.assertEqual(set(result["missing_receipts"]), set(MODULE.REQUIRED_FIELDS))
        self.assertEqual(result["invalid_receipts"], [])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertIsNone(result["approval_probability"])
        self.assertIsNone(result["fda_prediction"])

    def test_complete_receipts_remain_unverified(self):
        value = record()
        value["source_metadata"] = {key: {
            "url": "https://clinicaltrials.gov/study/NCT00000001",
            "excerpt": "A synthetic description of the supporting source.",
            "sha256": "a" * 64,
            "published_on": "2025-12-01",
        } for key in MODULE.REQUIRED_FIELDS}
        result = MODULE.inspect_metadata(value)
        self.assertEqual(result["missing_receipts"], [])
        self.assertEqual(result["invalid_receipts"], [])
        self.assertFalse(result["source_facts_independently_verified"])
        self.assertFalse(result["scientific_stage_complete"])
        self.assertIsNone(result["clinical_score"])

    def test_future_receipts_and_non_https_are_flagged(self):
        value = record()
        key = MODULE.REQUIRED_FIELDS[0]
        value["source_metadata"][key] = {
            "url": "http://localhost/private", "excerpt": "x" * 32,
            "sha256": "a" * 64, "published_on": "2026-02-01",
        }
        result = MODULE.inspect_metadata(value)
        self.assertIn(key, result["invalid_receipts"])

    def test_invalid_nct_phase_and_cutoff_fail_closed(self):
        value = record()
        for field, bad in (("nct", "NCT1"), ("trial_phase", "Phase 3"),
                           ("knowledge_cutoff", "not-a-date")):
            altered = dict(value)
            altered[field] = bad
            with self.assertRaises(ValueError):
                MODULE.inspect_metadata(altered)


if __name__ == "__main__":
    unittest.main()
