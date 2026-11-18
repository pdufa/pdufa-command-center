import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "scripts/validate_2026_rp1_review_cycles.py"
spec = importlib.util.spec_from_file_location("rp1_review_cycles", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def record(cycle="FIRST_RESUBMISSION_CLASS_II"):
    return {
        "application_id": "BLA125827",
        "review_cycle": cycle,
        "pdufa_goal_date": "2026-04-10",
        "fda_action_date": "2026-04-10",
        "fda_outcome": "CRL",
        "goal_source": "https://example.org/goal",
        "action_source": "https://example.org/action",
        "assessment_type": "OUTCOME_AWARE_REFERENCE",
        "l1_prediction": "",
    }

class ReviewCycleIntegrityTests(unittest.TestCase):
    def test_two_distinct_cycles_same_bla_are_valid(self):
        self.assertEqual(mod.validate([record(), record("SECOND_RESUBMISSION_CLASS_I")]), [])

    def test_duplicate_same_cycle_is_rejected(self):
        self.assertTrue(any("duplicate" in e for e in mod.validate([record(), record()])))

    def test_outcome_aware_prediction_is_rejected(self):
        row = record()
        row["l1_prediction"] = "APPROVE"
        self.assertTrue(any("invent L1 prediction" in e for e in mod.validate([row])))

    def test_missing_required_column_is_rejected(self):
        row = record()
        del row["review_cycle"]
        self.assertTrue(any("missing columns" in e for e in mod.validate([row])))

    def test_missing_source_is_rejected(self):
        row = record()
        row["goal_source"] = ""
        self.assertTrue(any("missing primary-source" in e for e in mod.validate([row])))

if __name__ == "__main__":
    unittest.main()
