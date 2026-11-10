import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from stage4_gate_coverage import coverage, GATES
from stage4_evidence_review_ledger import ROSTER

class GateCoverageTests(unittest.TestCase):
    def setUp(self):
        self.roster = json.loads(ROSTER.read_text(encoding="utf-8"))

    def test_empty_ledger_has_232_unreviewed_gates(self):
        report = coverage(self.roster, [])
        self.assertEqual(report["total_gates"], 232)
        self.assertEqual(report["documented_verified_gates"], 0)
        self.assertEqual(report["trials_with_all_gates_verified"], 0)
        self.assertTrue(all(all(s == "not_reviewed" for s in t["gates"].values()) for t in report["trials"]))

    def test_pending_review_is_not_verified(self):
        nct = self.roster["records"][0]["nct"]
        report = coverage(self.roster, [{"nct": nct, "category": GATES[0], "status": "pending"}])
        self.assertEqual(report["documented_verified_gates"], 0)
        self.assertEqual(report["trials"][0]["gates"][GATES[0]], "pending")

if __name__ == "__main__":
    unittest.main()
