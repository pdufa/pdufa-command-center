import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_retrieval_coverage_audit.py"
spec = importlib.util.spec_from_file_location("stage4_retrieval_coverage_audit", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.roster = json.loads((PATH.parents[1] / "new-platform/frontend/data/p3PostDataActive.json").read_text())
        ids = [r["nct"] for r in self.roster["records"]]
        self.registry = {"scientific_adjudications": 0, "trials": [{"nct": n, "status": "retrieved", "prediction": None} for n in ids]}
        self.triage = {"verified_scientific_adjudications": 0, "trials": [{"nct": n, "readiness": "phase_unresolved", "verified": False, "prediction": None} for n in ids]}

    def test_valid_unverified_coverage(self):
        result = module.audit(self.registry, self.triage, self.roster)
        self.assertEqual(result["retrieved"], 29)
        self.assertFalse(result["scientific_verification_complete"])

    def test_missing_trial_fails(self):
        self.registry["trials"].pop()
        with self.assertRaises(ValueError):
            module.audit(self.registry, self.triage, self.roster)

    def test_mismatched_trial_fails(self):
        self.triage["trials"][0]["nct"] = "NCT00000000"
        with self.assertRaises(ValueError):
            module.audit(self.registry, self.triage, self.roster)

    def test_premature_prediction_fails(self):
        self.registry["trials"][0]["prediction"] = 0.9
        with self.assertRaises(ValueError):
            module.audit(self.registry, self.triage, self.roster)


if __name__ == "__main__":
    unittest.main()
