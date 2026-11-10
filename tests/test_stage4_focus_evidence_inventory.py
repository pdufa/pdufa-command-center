import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "stage4_focus_evidence_inventory.py"
spec = importlib.util.spec_from_file_location("focus_evidence_inventory", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FocusEvidenceInventoryTests(unittest.TestCase):
    def test_canonical_roster(self):
        doc = json.loads(module.ROSTER.read_text(encoding="utf-8"))
        result = module.summarize(doc)
        self.assertEqual(result["focus_trials"], 29)
        self.assertFalse(result["source_links_are_verified"])
        self.assertEqual(result["independent_trial_adjudications_verified"], 0)

    def test_rejects_short_roster(self):
        with self.assertRaises(ValueError):
            module.summarize({"records": []})

    def test_rejects_duplicate_nct(self):
        records = [{"nct": f"NCT{i:08d}", "resultsUrl": "https://example.com", "regulatoryUrl": "https://example.com"} for i in range(29)]
        records[1]["nct"] = records[0]["nct"]
        with self.assertRaises(ValueError):
            module.summarize({"records": records})


if __name__ == "__main__":
    unittest.main()
