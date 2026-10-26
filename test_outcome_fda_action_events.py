import unittest
from datetime import date
from outcome_fda_action_events import FDAEvent, ModelGate, unique_final_actions, check_asof

FDA = "https://www.fda.gov/media/186513/download"

class OutcomeActionEventTests(unittest.TestCase):
    def event(self, kind, final=False, submission="BLA:125807:ORIG:0"):
        return FDAEvent("BLA:125807", submission, date(2025, 4, 28), kind, FDA, final, source_publication_date=date(2025, 4, 28))

    def test_default_gate_fails_closed(self):
        gate = ModelGate()
        self.assertFalse(gate.model_eligible)
        self.assertIsNone(gate.prediction_probability)

    def test_partial_gate_fails_closed(self):
        gate = ModelGate(True, True, True, True, False)
        self.assertFalse(gate.model_eligible)

    def test_review_recommendation_not_final_action(self):
        with self.assertRaises(ValueError):
            self.event("review_recommendation", True)
        self.assertEqual(unique_final_actions([self.event("review_recommendation")]), {})

    def test_incomplete_response_not_final_action(self):
        with self.assertRaises(ValueError):
            self.event("incomplete_response", True)

    def test_same_action_deduplicates(self):
        action = self.event("approval", True)
        self.assertEqual(len(unique_final_actions([action, action])), 1)

    def test_separate_submission_targets_not_collapsed(self):
        a = self.event("complete_response", True, "NDA:214410:ORIG:2")
        b = self.event("complete_response", True, "NDA:210854:SUPPL:05")
        self.assertEqual(len(unique_final_actions([a, b])), 2)

    def test_asof_missing_date_fails_closed(self):
        event = FDAEvent("BLA:125807", "ORIG", date(2025, 4, 28), "approval", FDA, True)
        self.assertFalse(check_asof(event, date(2025, 5, 1)))

    def test_future_publication_excluded(self):
        self.assertFalse(check_asof(self.event("approval", True), date(2025, 4, 27)))
        self.assertTrue(check_asof(self.event("approval", True), date(2025, 4, 28)))

    def test_invalid_source_rejected(self):
        with self.assertRaises(ValueError):
            FDAEvent("BLA:125807", "ORIG", date(2025, 4, 28), "approval", "http://example.com", True)

if __name__ == "__main__":
    unittest.main()
