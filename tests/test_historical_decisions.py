import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from historical_decisions import build_decisions


class HistoricalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.history = pd.DataFrame([
            {"event_key": "A", "ticker": "A", "pdufa_date": "2020-01-01", "actual_outcome": "APPROVED"},
            {"event_key": "B", "ticker": "B", "pdufa_date": "2020-01-02", "actual_outcome": "CRL"},
            {"event_key": "C", "ticker": "C", "pdufa_date": "2020-01-03", "actual_outcome": "APPROVED"},
        ])
        self.broad = pd.DataFrame([
            {"event_key": "A", "forced_direction": "APPROVED", "fallback_probability": "87", "source_layer": "FROZEN_MODEL_FORCE", "model_version": "frozen"},
            {"event_key": "B", "forced_direction": "CRL", "fallback_probability": "87", "source_layer": "EVENT_RISK_OVERRIDE", "model_version": "frozen"},
            {"event_key": "C", "forced_direction": "CRL", "fallback_probability": "40", "source_layer": "FROZEN_MODEL_FORCE", "model_version": "frozen"},
        ])
        self.strict = pd.DataFrame([{"event_key": "C", "qualified_direction": "APPROVED", "source_layer": "VERIFIED_PREDECISION_PROMOTION"}])

    def test_recorded_risk_override_is_not_replaced_by_probability(self):
        decisions = build_decisions(self.history, self.broad, self.strict).set_index("event_key")
        self.assertEqual(decisions.loc["B", "assessed_direction"], "CRL")
        self.assertEqual(decisions.loc["B", "baseline_model_probability_pct"], "87")
        self.assertEqual(decisions.loc["B", "strict_status"], "REVIEW_NO_CALL_ANALYZED")
        self.assertEqual(decisions.loc["C", "assessed_direction"], "APPROVED")
        self.assertEqual(decisions.loc["C", "assessment_basis"], "STRICT")

    def test_changing_outcomes_cannot_change_assessments(self):
        first = build_decisions(self.history, self.broad, self.strict)
        changed = self.history.copy()
        changed["actual_outcome"] = changed["actual_outcome"].map({"APPROVED": "CRL", "CRL": "APPROVED"})
        second = build_decisions(changed, self.broad, self.strict)
        unchanged = [c for c in first if c not in {"actual_outcome", "match_result"}]
        pd.testing.assert_frame_equal(first[unchanged], second[unchanged])
        self.assertTrue(second["match_result"].eq("MISS").all())

    def test_unresolved_outcome_is_not_scored_as_a_miss(self):
        history = self.history.copy()
        history.loc[0, "actual_outcome"] = "PENDING"
        decisions = build_decisions(history, self.broad, self.strict).set_index("event_key")
        self.assertEqual(decisions.loc["A", "match_result"], "PENDING")

    def test_identity_mismatch_and_duplicates_are_blocked(self):
        with self.assertRaises(ValueError):
            build_decisions(self.history, self.broad.iloc[:2], self.strict)
        with self.assertRaises(ValueError):
            build_decisions(self.history, pd.concat([self.broad, self.broad.iloc[:1]]), self.strict)


if __name__ == "__main__":
    unittest.main()
