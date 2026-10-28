import json
import tempfile
import unittest
from pathlib import Path
from research.fda_candidate_audit_cli import load_jsonl
from research.fda_candidate_audit import audit_candidates


class CandidateAuditCliTests(unittest.TestCase):
    def test_jsonl_rejects_non_object(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.jsonl"
            p.write_text('[]\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_jsonl(p)

    def test_candidate_union_cannot_be_training_cohort(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "sample.jsonl"
            p.write_text(json.dumps({"source_cohort": "candidate_union", "action_type": "approval"}) + "\n", encoding="utf-8")
            result = audit_candidates(load_jsonl(p))
            self.assertEqual(result["total_candidates"], 1)
            self.assertEqual(result["eligible_for_further_review"], 0)
            self.assertIsNone(result["approval_rate"])
            self.assertFalse(result["trading_authorized"])


if __name__ == "__main__":
    unittest.main()
