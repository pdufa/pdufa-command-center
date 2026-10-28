import csv
import json
import unittest
from pathlib import Path
from research.fda_legacy_accuracy_reconciliation import reconcile_legacy_accuracy

ROOT = Path(__file__).resolve().parents[1]

class LegacyAccuracyReconciliationTests(unittest.TestCase):
    def test_six_legacy_yes_flags_do_not_certify_prospective_accuracy(self):
        with (ROOT/"data/prediction_engine_audit.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        archive = json.loads((ROOT/"research/evidence/2025_holdout_archive_provenance_audit.json").read_text())
        cases = json.loads((ROOT/"research/evidence/2025_holdout_predecision_reconstruction.json").read_text())
        result = reconcile_legacy_accuracy(rows, archive, cases)
        self.assertEqual(result["legacy_rows_reconciled"], 6)
        self.assertEqual(result["verified_prospective_accuracy_cases"], 0)
        self.assertFalse(result["production_audit_modified"])
        self.assertTrue(all(row["legacy_count_in_audited_accuracy"] == "YES" for row in result["cases"]))
        self.assertTrue(all(not row["verified_prospective_accuracy_eligible"] for row in result["cases"]))

if __name__ == "__main__":
    unittest.main()
