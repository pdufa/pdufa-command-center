import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("queue", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_research_queue.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)

class ResearchQueueTests(unittest.TestCase):
    def fixture(self):
        return {"status": "EVIDENCE_GAPS_NOT_ASSESSMENTS", "trialCount": 29,
                "trials": [{"nct": f"NCT{i:08d}", "scientificAssessmentStatus": "NOT_ADJUDICATED",
                            "needsAdditionalEvidence": list(queue.DIMENSION_ORDER)} for i in range(29)]}

    def test_all_tasks_are_unreviewed(self):
        result = queue.build(self.fixture())
        self.assertEqual(result["taskCount"], 232)
        self.assertEqual(result["completedResearchTasks"], 0)
        self.assertTrue(all(t["scientificFinding"] is None for t in result["tasks"]))

    def test_reject_unknown_dimension(self):
        fixture = self.fixture()
        fixture["trials"][0]["needsAdditionalEvidence"] = ["made_up"]
        with self.assertRaises(ValueError):
            queue.build(fixture)

if __name__ == "__main__":
    unittest.main()
