"""Regression checks for FDA decision labeling. Run: python -m unittest discover -s tests -p 'test_fda_decision_taxonomy.py'"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fda_decision_taxonomy import classify_decision, deduplicate_applications


class DecisionTaxonomyTests(unittest.TestCase):
    def event(self, action="approval", **kwargs):
        return {"application_id": "NDA123456", "action": action,
                "decision_date": "2020-01-01",
                "source_url": "https://www.accessdata.fda.gov/example",
                **kwargs}

    def test_approval_pass(self):
        self.assertEqual(classify_decision(self.event(), as_of="2020-02-01")["label"], "PASS")

    def test_crl_fail_not_permanent_rejection(self):
        self.assertEqual(classify_decision(self.event("crl"), as_of="2020-02-01")["label"], "FAIL")

    def test_future_outcome_excluded(self):
        self.assertEqual(classify_decision(self.event(), as_of="2019-12-31")["status"], "future_event_excluded")

    def test_missing_source_excluded(self):
        event = self.event()
        event["source_url"] = ""
        self.assertFalse(classify_decision(event, as_of="2020-02-01")["eligible_for_binary_training"])

    def test_withdrawal_censored(self):
        self.assertEqual(classify_decision(self.event("withdrawn"), as_of="2020-02-01")["status"], "censored_or_out_of_scope")

    def test_unknown_requires_review(self):
        self.assertEqual(classify_decision(self.event("something_else"), as_of="2020-02-01")["status"], "unknown_action_requires_review")

    def test_duplicate_same_application_counted_once(self):
        result = deduplicate_applications([self.event(), self.event()], as_of="2020-02-01")
        self.assertEqual(result["counts"]["verified_applications"], 1)

    def test_conflicting_actions_flagged(self):
        result = deduplicate_applications([self.event(), self.event("crl")], as_of="2020-02-01")
        self.assertEqual(result["counts"]["conflicting_applications"], 1)
        self.assertEqual(result["counts"]["verified_applications"], 0)


if __name__ == "__main__":
    unittest.main()
