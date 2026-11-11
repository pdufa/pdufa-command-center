import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_phase_first_triage.py"
spec = importlib.util.spec_from_file_location("stage4_phase_first_triage", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_records():
    return [{"nct": f"NCT{i:08d}", "status": "retrieved", "phase": ["PHASE3"],
             "results_submitted": True} for i in range(29)]


class PhaseFirstTriageTests(unittest.TestCase):
    def test_results_do_not_equal_verification(self):
        result = module.triage({"trials": make_records()})
        self.assertEqual(result["verified_scientific_adjudications"], 0)
        self.assertEqual(result["trials"][0]["readiness"], "phase_appropriate_results_present")
        self.assertFalse(result["trials"][0]["verified"])

    def test_earlier_phase_not_held_to_phase3(self):
        records = make_records()
        records[0]["phase"] = ["PHASE2"]
        self.assertEqual(module.triage({"trials": records})["trials"][0]["readiness"], "earlier_phase")

    def test_missing_phase_is_unresolved(self):
        records = make_records()
        records[0]["phase"] = []
        self.assertEqual(module.triage({"trials": records})["trials"][0]["readiness"], "phase_unresolved")

    def test_failed_retrieval_cannot_pass(self):
        records = make_records()
        records[0] = {"nct": records[0]["nct"], "status": "retrieval_failed"}
        self.assertEqual(module.triage({"trials": records})["trials"][0]["readiness"], "retrieval_failed")

    def test_duplicate_rejected(self):
        records = make_records()
        records[1]["nct"] = records[0]["nct"]
        with self.assertRaises(ValueError):
            module.triage({"trials": records})


if __name__ == "__main__":
    unittest.main()
