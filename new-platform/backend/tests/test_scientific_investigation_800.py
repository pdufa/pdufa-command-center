"""Offline, synthetic-only checks for a 20-depth, 800-slot science plan."""
import unittest
from collections import Counter

from app.scientific_investigation_contract import (
    DEPTH_LEVELS, LAYERS, investigation_plan,
)
from app.scientific_investigation_800 import (
    INVESTIGATION_DEPTHS, build_investigation_800,
)


class Investigation800Tests(unittest.TestCase):
    def test_exact_40_by_20_has_800_unique_pending_tasks(self):
        result = build_investigation_800("NCT02142738")
        self.assertEqual(result["exactId"], "TRIAL|NCT02142738")
        self.assertEqual(result["layers"], 8)
        self.assertEqual(result["assessments"], 40)
        self.assertEqual(result["depthCount"], 20)
        self.assertEqual(result["requiredTasks"], 800)
        self.assertEqual(len(result["tasks"]), 800)
        self.assertEqual(len({t["taskId"] for t in result["tasks"]}), 800)
        self.assertEqual(len({t["assessmentId"] for t in result["tasks"]}), 40)
        self.assertEqual(
            set(Counter(t["assessmentId"] for t in result["tasks"]).values()),
            {20},
        )
        self.assertEqual(
            set(Counter(t["depthLevel"] for t in result["tasks"]).values()),
            {40},
        )
        self.assertEqual([d["level"] for d in result["depths"]], list(range(1, 21)))
        self.assertEqual(result["completedTasks"], 0)
        self.assertEqual(result["independentlyVerifiedTasks"], 0)
        self.assertFalse(result["analysisReady"])

    def test_no_fake_reviews_scores_grades_or_probabilities(self):
        result = build_investigation_800("NCT04280705")
        for key in (
            "readinessGrade", "reluctantGrade",
            "scientificConclusion", "approvalProbability",
        ):
            self.assertIsNone(result[key])
        for task in result["tasks"]:
            self.assertEqual(task["reviewStatus"], "pending_independent_review")
            self.assertFalse(task["independentlyVerified"])
            self.assertIsNone(task["scientificScore"])
            self.assertEqual(task["reviewerA"], "not_assigned")
            self.assertEqual(task["reviewerB"], "not_assigned")

    def test_twenty_depth_names_match_requested_methods(self):
        self.assertEqual(len(INVESTIGATION_DEPTHS), 20)
        self.assertEqual(INVESTIGATION_DEPTHS[0][1], "Document Reading")
        self.assertEqual(INVESTIGATION_DEPTHS[-1][1], "Red-Team Adjudication")
        self.assertIn(("bayesian_integration", "Bayesian Integration"),
                      INVESTIGATION_DEPTHS)

    def test_exact_trial_required_and_no_ticker_inference(self):
        for bad in (
            "", "OCUL", "TRIAL|NCT02142738", "APPLICATION|1234",
            "NCT123", "NCT021427380", "nct02142738", "../NCT02142738", None,
        ):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(ValueError, "Exact NCT ID"):
                    build_investigation_800(bad)

    def test_legacy_320_task_workflow_is_unchanged(self):
        self.assertEqual(len(DEPTH_LEVELS), 8)
        self.assertEqual(len(LAYERS), 8)
        legacy = investigation_plan()
        self.assertEqual(legacy["requiredTasks"], 320)
        self.assertEqual(len(legacy["tasks"]), 320)
        modern = build_investigation_800("NCT02142738")
        self.assertNotEqual(legacy["schemaVersion"], modern["schemaVersion"])
        self.assertEqual(legacy["approvalProbability"], None)
        self.assertEqual(modern["approvalProbability"], None)


if __name__ == "__main__":
    unittest.main()
