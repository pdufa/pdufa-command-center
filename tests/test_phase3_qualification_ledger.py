import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import phase3_qualification_ledger as q

class QualificationLedgerTests(unittest.TestCase):
    def test_full_census_requires_no_automatic_promotion(self):
        with q.CENSUS.open(encoding="utf-8-sig", newline="") as f:
            census = list(csv.DictReader(f))
        report = {"census_total": 741, "original_source_records": [
            {"nct_id": r["nct_id"], "census_ticker": r["ticker"],
             "census_company": r["company"], "source_sha256": "a" * 64,
             "source": "https://clinicaltrials.gov/api/v2/studies/" + r["nct_id"],
             "phase3_in_current_registry": True, "status_matches_dated_census": True}
            for r in census
        ]}
        result = q.build_ledger(report)
        self.assertEqual(result["total"], 741)
        self.assertEqual(result["source_verified"], 741)
        self.assertIsNone(result["qualified_pipeline_total"])
        self.assertTrue(all(r["qualification_status"] == "REVIEW" for r in result["records"]))
        self.assertTrue(all(r["qualified_pipeline"] is None for r in result["records"]))
        for gate in q.GATES[1:]:
            self.assertEqual(result["gate_counts"][gate].get("REVIEW"), 741)

    def test_missing_source_cannot_pass(self):
        result = q.build_ledger({"census_total": 741, "original_source_records": []})
        self.assertEqual(result["source_verified"], 0)
        self.assertEqual(result["gate_counts"]["registry_identity"]["REVIEW"], 741)

    def test_unrelated_nct_rejected(self):
        with self.assertRaises(ValueError):
            q.build_ledger({"census_total": 741, "original_source_records": [{"nct_id": "NCT99999999"}]})

    def test_wrong_denominator_rejected(self):
        with self.assertRaises(ValueError):
            q.build_ledger({"census_total": 740, "original_source_records": []})

if __name__ == "__main__":
    unittest.main()
