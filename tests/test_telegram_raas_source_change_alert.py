"""Unit-test RAAS saved-evidence Telegram alert boundaries without network."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.telegram_raas_source_change_alert import (
    SCOPE, COMPARED, verified_research_delta_summary, main,
)
from scripts.telegram_scan_alert import message


def report():
    return {
        "schemaVersion": 1,
        "scope": SCOPE,
        "sourceChangeComparisonStatus": COMPARED,
        "sourceChangedSincePreviousRun": True,
        "savedSourceEvidenceFingerprint": "f" * 64,
        "auditStateFingerprint": "a" * 64,
        "counts": {
            "independentlyAuthenticatedForecasts": 0,
            "qualifiedForecastOutcomePairs": 0,
            "approvedTradingSignals": 0,
        },
        "threeWayScorecard": {"independentValidatedAccuracyPct": None},
        "records": [],
        "savedSourceChanges": [{
            "caseKey": "COGT-BEZUCLASTINIB-GIST-2026",
            "type": "SAVED_SOURCE_OR_INTAKE_METADATA_CHANGED",
            "changedEvidenceFields": ["sourceFingerprint", "sourceUrl"],
            "fdaDecisionVerified": False,
        }],
    }


class RAASSourceChangeTelegramTests(unittest.TestCase):
    def test_valid_source_change_notice_is_clearly_unverified(self):
        details = verified_research_delta_summary(report())
        self.assertIn("1 application/cycle", details)
        self.assertIn("1 updated, 0 added, 0 removed", details)
        self.assertIn("No independently adjudicated FDA outcome", details)
        self.assertNotIn("COGT", details)
        self.assertNotIn("https:", details)
        alert = message("raas-evidence-change", details=details)
        self.assertIn("RESEARCH EVIDENCE CHANGED", alert)
        self.assertNotIn("VERIFIED PREDICTION CHANGE", alert)

    def test_first_run_calendar_change_or_invalid_previous_never_alerts(self):
        for invalid in [
            {**report(), "sourceChangeComparisonStatus":
             "NO_PREVIOUS_RUN_ARTIFACT_PROVIDED"},
            {**report(), "sourceChangeComparisonStatus":
             "PREVIOUS_ARTIFACT_INVALID_NO_COMPARISON"},
            {**report(), "sourceChangedSincePreviousRun": False},
            {**report(), "sourceChangedSincePreviousRun": None},
            {**report(), "savedSourceChanges": []},
            {**report(), "savedSourceChanges": None},
        ]:
            self.assertIsNone(verified_research_delta_summary(invalid))
        calendar = {
            **report(),
            "sourceChangedSincePreviousRun": False,
            "savedSourceChanges": [],
            "calendarDeadlineTransitions": [{
                "caseKey": "COGT-BEZUCLASTINIB-GIST-2026",
                "type": "ORIGINAL_GOAL_CALENDAR_ELAPSED_NOT_OFFICIAL_FDA_OUTCOME",
            }],
        }
        self.assertIsNone(verified_research_delta_summary(calendar))

    def test_missing_gates_prevent_a_false_alert(self):
        for bad in [
            {"schemaVersion": 2},
            {**report(), "scope": "ACTUAL_FDA_OUTCOME"},
            {**report(), "auditStateFingerprint": "wrong"},
            {**report(), "savedSourceEvidenceFingerprint": "wrong"},
            {**report(), "counts": {**report()["counts"],
                                   "independentlyAuthenticatedForecasts": 1}},
            {**report(), "counts": {**report()["counts"],
                                   "qualifiedForecastOutcomePairs": 1}},
            {**report(), "counts": {**report()["counts"],
                                   "approvedTradingSignals": 1}},
            {**report(), "threeWayScorecard":
             {"independentValidatedAccuracyPct": 90}},
            {**report(), "savedSourceChanges": [{
                **report()["savedSourceChanges"][0],
                "fdaDecisionVerified": True,
            }]},
            {**report(), "savedSourceChanges": [{
                **report()["savedSourceChanges"][0],
                "type": "FDA_APPROVED",
            }]},
            {**report(), "savedSourceChanges": [{
                **report()["savedSourceChanges"][0],
                "changedEvidenceFields": ["fdaApprovalReported"],
            }]},
            {**report(), "savedSourceChanges": [{
                **report()["savedSourceChanges"][0],
                "caseKey": "injected\nsecret-token",
            }]},
            {**report(), "savedSourceChanges": [
                report()["savedSourceChanges"][0],
                report()["savedSourceChanges"][0],
            ]},
        ]:
            self.assertIsNone(verified_research_delta_summary(bad))

    def test_added_removed_case_alerts_without_claiming_fda_action(self):
        r = report()
        r["savedSourceChanges"] = [
            {"caseKey": "TEST-RESEARCH-CASE-A",
             "type": "SAVED_RESEARCH_CASE_ADDED",
             "changedEvidenceFields": ["caseKey"], "fdaDecisionVerified": False},
            {"caseKey": "TEST-RESEARCH-CASE-B",
             "type": "SAVED_RESEARCH_CASE_REMOVED",
             "changedEvidenceFields": ["caseKey"], "fdaDecisionVerified": False},
        ]
        self.assertIn("0 updated, 1 added, 1 removed",
                      verified_research_delta_summary(r))
        r["savedSourceChanges"][0]["changedEvidenceFields"] = ["sourceUrl"]
        self.assertIsNone(verified_research_delta_summary(r))

    def test_cli_dry_run_no_message_for_missing_prior_comparison(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "report.json"
            file.write_text(json.dumps({
                **report(), "sourceChangedSincePreviousRun": None,
                "savedSourceChanges": None,
                "sourceChangeComparisonStatus":
                "NO_PREVIOUS_RUN_ARTIFACT_PROVIDED",
            }))
            output = io.StringIO()
            with patch("scripts.telegram_raas_source_change_alert.send_telegram") as sender:
                with redirect_stdout(output):
                    self.assertEqual(main(["--report", str(file), "--dry-run"]), 0)
                sender.assert_not_called()
            self.assertIn("No authenticated run-to-run", output.getvalue())

    def test_cli_dry_run_can_format_without_secrets_or_network(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "report.json"
            file.write_text(json.dumps(report()))
            output = io.StringIO()
            with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "",
                                         "TELEGRAM_CHAT_ID": ""}):
                with redirect_stdout(output):
                    code = main(["--report", str(file), "--dry-run",
                                 "--run-url",
                                 "https://github.com/pdufa/pdufa-command-center/actions/runs/42"])
            self.assertEqual(code, 0)
            self.assertIn("RAAS — SAVED RESEARCH EVIDENCE CHANGED", output.getvalue())
            self.assertIn("actions/runs/42", output.getvalue())
            self.assertNotIn("COGT", output.getvalue())

    def test_invalid_json_report_suppresses_all_notifications(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "report.json"
            file.write_text("{broken")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(main(["--report", str(file), "--dry-run"]), 0)
            self.assertIn("missing/invalid", out.getvalue())


if __name__ == "__main__":
    unittest.main()
