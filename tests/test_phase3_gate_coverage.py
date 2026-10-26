import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from phase3_qualification_ledger import GATES
from phase3_gate_coverage import summarize

class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"total": 741, "records": [
            {"nct_id": f"NCT{i:08d}", "gates": {g: "REVIEW" for g in GATES}}
            for i in range(1, 742)]}
        self.intake = {"ledger_total": 741, "submitted_total": 0,
                       "qualified_pipeline_total": None, "items": []}
    def test_empty_intake_has_full_missing_denominators(self):
        report = summarize(self.ledger, self.intake)
        self.assertEqual(report["mandatory_gate_total"], 9)
        self.assertEqual(report["externally_reviewed_gate_total"], 8)
        self.assertTrue(all(x["records_without_evidence"] == 741 for x in report["coverage"].values()))
        self.assertIsNone(report["qualified_pipeline_total"])
    def test_distinct_study_coverage_not_item_count(self):
        self.intake["items"] = [
            {"nct_id": "NCT00000001", "gate": "public_listing", "reviewer_status": s,
             "intake_status": "EVIDENCE_RECORDED_NOT_QUALIFIED"} for s in ("PENDING", "ACCEPTED")]
        self.intake["submitted_total"] = 2
        r = summarize(self.ledger, self.intake)["coverage"]["public_listing"]
        self.assertEqual((r["evidence_items"], r["records_with_evidence"], r["records_without_evidence"]), (2, 1, 740))
    def test_unknown_study_fails_closed(self):
        self.intake["items"] = [{"nct_id": "NCT99999999", "gate": "public_listing",
            "reviewer_status": "PENDING", "intake_status": "EVIDENCE_RECORDED_NOT_QUALIFIED"}]
        self.intake["submitted_total"] = 1
        with self.assertRaises(ValueError):
            summarize(self.ledger, self.intake)
    def test_malformed_intake_fails_closed(self):
        self.intake["qualified_pipeline_total"] = 1
        with self.assertRaises(ValueError):
            summarize(self.ledger, self.intake)
if __name__ == "__main__":
    unittest.main()
