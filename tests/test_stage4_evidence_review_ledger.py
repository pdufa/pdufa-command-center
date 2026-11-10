import importlib.util
import json
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts/stage4_evidence_review_ledger.py"
spec = importlib.util.spec_from_file_location("stage4_ledger", PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
roster = json.loads(mod.ROSTER.read_text(encoding="utf-8"))

class EvidenceLedgerTests(unittest.TestCase):
    def test_empty_ledger_does_not_claim_verification(self):
        self.assertEqual(mod.validate(roster, [])["documented_verifications"], 0)

    def test_verified_requires_source_and_reviewer(self):
        with self.assertRaises(ValueError):
            mod.validate(roster, [{"nct": roster["records"][0]["nct"], "category": "efficacy", "status": "verified"}])

    def test_pending_does_not_count(self):
        entry = {"nct": roster["records"][0]["nct"], "category": "efficacy", "status": "pending"}
        self.assertEqual(mod.validate(roster, [entry])["documented_verifications"], 0)

    def test_unknown_trial_rejected(self):
        with self.assertRaises(ValueError):
            mod.validate(roster, [{"nct": "NCT00000000", "category": "efficacy", "status": "pending"}])

    def test_duplicate_category_rejected(self):
        entry = {"nct": roster["records"][0]["nct"], "category": "efficacy", "status": "pending"}
        with self.assertRaises(ValueError):
            mod.validate(roster, [entry, entry])

if __name__ == "__main__":
    unittest.main()
