import csv
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import importlib.util

spec = importlib.util.spec_from_file_location(
    "reconcile", Path(__file__).with_name("reconcile_2026_pdufa_ledger.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FIELDS = ("source,source_record_id,ticker,drug,indication,decision_date,"
          "application_id,source_url,source_status,source_retrieved_at\n")
def row(identifier, ticker, application, indication="Disease A", status="decided"):
    return f"archive,{identifier},{ticker},Drug X,{indication},2026-06-01,{application},https://example.org/{identifier},{status},2026-11-17\n"

class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source.csv"
        self.candidates = root / "candidates.csv"
        self.issues = root / "issues.csv"

    def run_reconcile(self):
        mod.reconcile(self.source, self.candidates, self.issues)
        with self.candidates.open(newline="") as f:
            accepted = list(csv.DictReader(f))
        with self.issues.open(newline="") as f:
            issues = list(csv.DictReader(f))
        return accepted, issues

    def test_deduplicates_multi_ticker_application(self):
        self.source.write_text(FIELDS + row("1", "AAA", "NDA123") +
                               row("2", "BBB", "NDA123") +
                               row("3", "CCC", "NDA456"))
        accepted, issues = self.run_reconcile()
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["ticker"], "CCC")
        self.assertEqual(len(issues), 2)

    def test_flags_missing_and_unfinalized(self):
        self.source.write_text(FIELDS + row("1", "AAA", "") +
                               row("2", "BBB", "NDA2", status="pending"))
        accepted, issues = self.run_reconcile()
        self.assertEqual(len(accepted), 0)
        self.assertEqual(len(issues), 2)

    def test_rejects_outcome_columns(self):
        self.source.write_text(FIELDS.strip() + ",actual_outcome\n" +
                               row("1", "AAA", "NDA1").strip() + ",APPROVE\n")
        with self.assertRaises(ValueError):
            self.run_reconcile()

if __name__ == "__main__":
    unittest.main()
