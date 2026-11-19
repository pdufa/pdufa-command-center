"""Outcome-independent regression tests for Level 1 qualitative rubric."""
import importlib.util
from pathlib import Path
import unittest

p = Path(__file__).resolve().parents[1] / "scripts/score_2026_l1_blind_rubric.py"
spec = importlib.util.spec_from_file_location("blind_rubric", p)
module = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = module
spec.loader.exec_module(module)

class BlindRubricTests(unittest.TestCase):
    def test_supportive_complete_packet(self):
        self.assertEqual(module.classify(module.EvidenceRatings(
            "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE")), "APPROVAL_LEAN")

    def test_missing_efficacy_statistics_abstains(self):
        self.assertEqual(module.classify(module.EvidenceRatings(
            "UNKNOWN", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE")), "ABSTAIN")

    def test_documented_material_manufacturing_concern(self):
        self.assertEqual(module.classify(module.EvidenceRatings(
            "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "CONCERN", "SUPPORTIVE",
            ("regulatory_pathway",))), "NONAPPROVAL_LEAN")

    def test_concern_without_documentation_abstains(self):
        self.assertEqual(module.classify(module.EvidenceRatings(
            "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "CONCERN", "SUPPORTIVE")), "ABSTAIN")

    def test_unknown_material_concern_rejected(self):
        with self.assertRaises(ValueError):
            module.classify(module.EvidenceRatings(
                "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "UNKNOWN", "SUPPORTIVE",
                ("regulatory_pathway",)))

    def test_bad_domain_rejected(self):
        with self.assertRaises(ValueError):
            module.classify(module.EvidenceRatings(
                "LIKELY", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE", "SUPPORTIVE"))

if __name__ == "__main__":
    unittest.main()
