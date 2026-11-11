import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_focus_evidence_review.py"
spec = importlib.util.spec_from_file_location("focus_evidence_review", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class EvidenceReviewTests(unittest.TestCase):
    def test_worklist_is_unverified_and_complete(self):
        doc = json.loads(module.ROSTER.read_text(encoding="utf-8"))
        output = module.make_worklist(doc)
        self.assertEqual(len(output["trials"]), 29)
        self.assertEqual(output["verified_predictions"], 0)
        self.assertTrue(all(t["adjudication"] is None and t["prediction"] is None for t in output["trials"]))
        self.assertTrue(all(t["evidence_status"] == "unverified" for t in output["trials"]))

    def test_rejects_duplicates(self):
        doc = json.loads(module.ROSTER.read_text(encoding="utf-8"))
        doc["records"][1]["nct"] = doc["records"][0]["nct"]
        with self.assertRaises(ValueError):
            module.make_worklist(doc)

    def test_rejects_missing_records(self):
        with self.assertRaises(ValueError):
            module.make_worklist({"records": []})


if __name__ == "__main__":
    unittest.main()
