import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("queue", Path(__file__).resolve().parents[1] / "scripts/medical/subspecialty_research_queue.py")
queue = importlib.util.module_from_spec(spec)
spec.loader.exec_module(queue)

class SpecialistQueueTests(unittest.TestCase):
    def fixture(self):
        return {"status": "EVIDENCE_GAPS_NOT_ASSESSMENTS", "trials": [
            {"nct": f"NCT{i:08d}", "needsAdditionalEvidence": list(queue.DIMENSION_ORDER[:5]),
             "registryLeadDimensions": list(queue.DIMENSION_ORDER[5:])} for i in range(29)]}

    def test_all_232_tasks_unreviewed(self):
        result = queue.build(self.fixture())
        self.assertEqual(result["taskCount"], 232)
        self.assertEqual(result["scientificAssessmentsCompleted"], 0)
        self.assertTrue(all(i["clinicalAssessmentStatus"] == "NOT_ADJUDICATED" for i in result["items"]))
        self.assertEqual(sum(i["researchTask"] == "LOCATE_EXTERNAL_EVIDENCE" for i in result["items"]), 145)

    def test_reject_dimension_overlap(self):
        fixture = self.fixture()
        fixture["trials"][0]["registryLeadDimensions"].append(queue.DIMENSION_ORDER[0])
        with self.assertRaises(ValueError):
            queue.build(fixture)

if __name__ == "__main__":
    unittest.main()
