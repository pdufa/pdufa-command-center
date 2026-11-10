"""Regression tests for the read-only Level 4 protocol inventory."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "medical" / "level4_protocol_audit.py"
spec = importlib.util.spec_from_file_location("level4_protocol_audit", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Level4AuditTests(unittest.TestCase):
    def test_source_pointer_is_not_scientific_review(self):
        preview = {"applications": [{
            "id": "provisional-1", "ticker": "TEST", "nctIds": ["NCT00000001"],
            "sources": [{"identifiers": ["NCT00000001"]}]
        }]}
        result = module.audit(preview)
        self.assertEqual(result["trialCount"], 1)
        self.assertEqual(result["completedProtocolReviews"], 0)
        self.assertTrue(result["trials"][0]["registry_pointer_captured"])
        self.assertEqual(result["trials"][0]["level4_status"], "REQUIRES_ORIGINAL_PROTOCOL_REVIEW")
        self.assertIn("statistical_analysis_plan", result["trials"][0]["required_checks"])

    def test_missing_source_remains_pending(self):
        result = module.audit({"applications": [{
            "id": "provisional-2", "ticker": "TEST", "nctIds": ["NCT00000002"], "sources": []
        }]})
        self.assertFalse(result["trials"][0]["registry_pointer_captured"])
        self.assertEqual(result["completedProtocolReviews"], 0)

    def test_empty_inventory_does_not_invent_predictions(self):
        result = module.audit({"applications": []})
        self.assertEqual(result["trialCount"], 0)
        self.assertEqual(result["trials"], [])
        self.assertEqual(result["completedProtocolReviews"], 0)

    def test_duplicate_nct_count_is_unique(self):
        app = lambda ident: {"id": ident, "ticker": "TEST", "nctIds": ["NCT00000003"], "sources": []}
        result = module.audit({"applications": [app("a"), app("b")]})
        self.assertEqual(result["trialCount"], 1)
        self.assertEqual(result["applicationRows"], 2)


if __name__ == "__main__":
    unittest.main()
