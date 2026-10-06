import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from strict_historical_review import assess_event, run_review
from fda_decision_engine import load_config

class StrictHistoricalReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT / "data/strict_historical_126_inputs.json").read_text())
        cls.cfg = load_config()

    def test_exact_126_coverage_and_real_engine_outputs(self):
        result = run_review(self.payload, self.cfg)
        self.assertEqual(len(result), 126)
        self.assertEqual(result.event_key.nunique(), 126)
        calls = dict(zip(result.event_key, result.fda_prediction))
        self.assertEqual(calls["PRVB|2021-07-02|teplizumab"], "CRL")
        self.assertEqual(calls["AKBA|2022-03-29|vadadustat"], "CRL")
        # An unspecified deficiency / clinical hold does not fabricate a scored failure.
        self.assertEqual(calls["ASND|2023-04-30|transcon-pth"], "REVIEW")
        self.assertEqual(calls["AKBA|2024-03-27"], "REVIEW")

    def test_outcomes_and_broad_scores_cannot_change_calls(self):
        changed = copy.deepcopy(self.payload)
        for event in changed["events"]:
            event.update(actual_outcome="APPROVED", actual_fda_decision="APPROVED", p_approval=1.0,
                         forced_direction="APPROVED", public_model_class="APPROVED")
        a, b = run_review(self.payload, self.cfg), run_review(changed, self.cfg)
        self.assertEqual(a.to_dict("records"), b.to_dict("records"))

    def test_late_or_unmatched_source_cannot_generate_crl(self):
        event = next(e for e in self.payload["events"] if e["ticker"] == "PRVB")
        for mutation in ("late", "identity", "availability", "cutoff"):
            bad = copy.deepcopy(event)
            if mutation == "late": bad["gate_evidence"][0]["published_date"] = bad["action_date"]
            if mutation == "identity": bad["gate_evidence"][0]["identity_verified"] = False
            if mutation == "availability": bad["gate_evidence"][0]["availability_verified"] = False
            if mutation == "cutoff": bad["evidence_cutoff"] = bad["action_date"]
            result = assess_event(bad, self.cfg)
            self.assertEqual(result["fda_prediction"], "REVIEW", mutation)
            self.assertEqual(result["admitted_evidence_count"], 0, mutation)

    def test_manifest_and_model_mismatches_fail_closed(self):
        bad = copy.deepcopy(self.payload)
        bad["events"][-1] = bad["events"][0]
        with self.assertRaises(ValueError): run_review(bad, self.cfg)
        bad = copy.deepcopy(self.payload)
        bad["events"][0]["ticker"] = "WRONG"
        with self.assertRaises(ValueError): run_review(bad, self.cfg)
        cfg = {**self.cfg, "model_version": "DIFFERENT"}
        with self.assertRaises(ValueError): run_review(self.payload, cfg)

if __name__ == "__main__": unittest.main()
