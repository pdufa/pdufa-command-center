import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_blind_six_levels_2026 as report


class SixLevelReportingTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        directory = Path(temp.name)
        self.args = SimpleNamespace(
            output=directory / "summary.json",
            summary_csv=directory / "summary.csv",
            results_csv=directory / "details.csv",
            locked=directory / "locked.json",
            outcomes=directory / "outcomes.csv",
            expected_lock_sha256="test-frozen-digest",
        )
        self.args.locked.write_text(json.dumps({
            "protocol": "TEST_ONLY",
            "expected_events": 3,
        }))
        self.rows = [
            {"event_id": case, "level": level, "prediction": prediction, "drug": "=test"}
            for level in report.LEVELS
            for case, prediction in (
                ("A", "APPROVE"), ("B", "APPROVE"), ("C", "ABSTAIN")
            )
        ]
        self.verify_lock = Mock(return_value=self.rows)
        self.load_csv = Mock(return_value=[
            {"event_id": "A", "actual_outcome": "APPROVE"},
            {"event_id": "B", "actual_outcome": "CRL"},
            {"event_id": "C", "actual_outcome": "CRL"},
        ])

    def test_outputs_show_abstentions_coverage_confusion_and_interval(self):
        report.score(self.args, self.verify_lock, self.load_csv)
        summary = json.loads(self.args.output.read_text())
        self.assertEqual([row["level"] for row in summary], list(report.LEVELS))
        first = summary[0]
        self.assertEqual((first["correct"], first["incorrect"], first["abstained"]), (1, 1, 1))
        self.assertAlmostEqual(first["coverage"], 2 / 3)
        self.assertAlmostEqual(first["accuracy"], 0.5)
        self.assertAlmostEqual(first["accuracy_ci95_wilson_low"], 0.09453, places=4)
        self.assertAlmostEqual(first["accuracy_ci95_wilson_high"], 0.90547, places=4)
        self.assertAlmostEqual(first["always_approve_accuracy_all"], 1 / 3)
        self.assertEqual(first["actual_crl_predicted_abstain"], 1)
        with self.args.results_csv.open(encoding="utf-8-sig", newline="") as stream:
            details = list(csv.DictReader(stream))
        self.assertEqual(len(details), 18)
        self.assertEqual(details[0]["drug"], "'=test")
        self.assertEqual(details[2]["correct"], "")
        with self.args.summary_csv.open(encoding="utf-8-sig", newline="") as stream:
            self.assertEqual(len(list(csv.DictReader(stream))), 6)

    def test_all_abstentions_leave_accuracy_and_interval_unavailable(self):
        for row in self.rows:
            row["prediction"] = "ABSTAIN"
        report.score(self.args, self.verify_lock, self.load_csv)
        summary = json.loads(self.args.output.read_text())
        self.assertEqual(summary[0]["coverage"], 0)
        self.assertIsNone(summary[0]["accuracy"])
        self.assertIsNone(summary[0]["accuracy_ci95_wilson_low"])
        self.assertIsNone(summary[0]["accuracy_ci95_wilson_high"])

    def test_invalid_lock_keeps_outcomes_unopened(self):
        self.verify_lock.side_effect = ValueError("Invalid lock")
        with self.assertRaisesRegex(ValueError, "Invalid lock"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.load_csv.assert_not_called()

    def test_missing_or_duplicate_assessment_keeps_outcomes_unopened(self):
        self.rows.pop()
        with self.assertRaisesRegex(ValueError, "all six levels"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.rows.append(self.rows[0])
        with self.assertRaisesRegex(ValueError, "Duplicate locked assessment"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.load_csv.assert_not_called()

    def test_outcomes_require_exact_ids_and_binary_verified_actions(self):
        self.load_csv.return_value.pop()
        with self.assertRaisesRegex(ValueError, "Event IDs differ"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.load_csv.return_value.append({"event_id": "C", "actual_outcome": "WITHDRAWN"})
        with self.assertRaisesRegex(ValueError, "Unsupported outcome"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.assertFalse(self.args.output.exists())

    def test_output_path_cannot_overwrite_a_lock_or_outcome_file(self):
        self.args.results_csv = self.args.outcomes
        with self.assertRaisesRegex(ValueError, "separate from input files"):
            report.score(self.args, self.verify_lock, self.load_csv)
        self.load_csv.assert_not_called()


class CanonicalLedgerTests(unittest.TestCase):
    def setUp(self):
        self.identity = {
            "event_id": "FIXTURE",
            "application_number": "NDA000000",
            "review_cycle": "original-1",
            "decision_date": "2026-04-21",
        }
        self.action = {
            **self.identity,
            "identity_status": "VERIFIED_ELIGIBLE",
            "fda_source_url": "https://www.fda.gov/fixture",
            "actual_outcome": "APPROVE",
        }

    def test_verified_identity_matches(self):
        from score_scientific_backtest_2026 import validate_ledger

        validate_ledger([self.action], [self.identity])

    def test_rejects_wrong_cycle_unresolved_action_and_unofficial_url(self):
        from score_scientific_backtest_2026 import validate_ledger

        for field, value, message in (
            ("review_cycle", "resubmission-2", "locked application cycle"),
            ("identity_status", "SOURCE_CORROBORATED_SUBSET", "not verified eligible"),
            ("fda_source_url", "https://fda.gov.example.org/fixture", "official FDA source"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                validate_ledger([{**self.action, field: value}], [self.identity])
