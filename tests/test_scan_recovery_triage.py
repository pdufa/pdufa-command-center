"""Regression: only safe recovery planning, never source promotion or auto-code edits."""
import unittest

from scripts.scan_recovery_triage import (
    build_report, classify, triage_source_rows, triage_code_failures
)

def issue(category="SEC", claim="FINANCING_CLOSURE", state="REVIEW_REQUIRED",
          key="COGT|BEZUCLASTINIB_GIST_20261130"):
    return {
        "ticker": key.split("|")[0],
        "event_key": key,
        "category": category,
        "claim": claim,
        "verification_status": state,
        "verification_required": "YES",
        "reason": "Missing independent issuer-matched closing statement",
        "source_url": "",
    }


class RecoveryTriageTests(unittest.TestCase):
    def test_financing_pending_remains_blocked(self):
        r = triage_source_rows([issue()], {
            "required_findings_unresolved": 1, "latest_run_id": "100"
        })
        self.assertEqual(r["status"], "READY_FOR_NEXT_NIGHT_RECHECK")
        self.assertEqual(r["items"][0]["next_scan_action"], "RECHECK_CIK_MATCHED_SEC_FINANCING")
        self.assertFalse(r["items"][0]["auto_verified"])
        self.assertEqual(r["items"][0]["gem_trade_entry"], "BLOCKED_FROM_THIS_FINDING")

    def test_fda_and_clinical_conflicts_never_turn_into_proof(self):
        rows = [issue("FDA", "PDUFA_TARGET", "REVIEW_REQUIRED", "X|A"),
                issue("ISSUER", "ISSUER_RELEASE", "CONFLICT", "Y|B")]
        report = build_report(rows, {
            "latest_run_id": "123", "required_findings_unresolved": 2
        }, source_run_id="123")
        self.assertTrue(report["source_snapshot_matches_current_run"])
        self.assertEqual(report["queue_status"], "READY_FOR_NEXT_NIGHT_RECHECK")
        self.assertEqual(report["next_scan_actions"]["HOLD_CONFLICT_AND_RECHECK_PRIMARY"], 1)
        self.assertEqual(report["next_scan_actions"]["RECHECK_ISSUER_FDA_TARGET"], 1)
        self.assertFalse(report["gem_trade_entry_authorized"])
        self.assertFalse(report["automatic_evidence_promotion_enabled"])

    def test_missing_or_previous_report_is_not_fresh(self):
        report = build_report([issue()], {
            "latest_run_id": "100", "required_findings_unresolved": 1
        }, source_run_id="101")
        self.assertFalse(report["source_snapshot_matches_current_run"])
        self.assertEqual(report["queue_status"], "PREVIOUS_SNAPSHOT_PENDING_SOURCE_PUBLICATION")

    def test_duplicate_identity_or_missing_row_count_is_hold(self):
        one = issue()
        status = triage_source_rows([one, one], {
            "required_findings_unresolved": 2
        })
        self.assertEqual(status["status"], "INCOMPLETE_IDENTITY_CONFLICT")
        mismatch = triage_source_rows([one], {
            "required_findings_unresolved": 2
        })
        self.assertEqual(mismatch["status"], "INCOMPLETE_OR_STALE_QUEUE")
        self.assertEqual(mismatch["findings_count"], 1)

    def test_code_failures_are_diagnostic_except_one_existing_safe_retry(self):
        alerts = {"github": {"current_failures": [
            {"id": 123, "workflow": "ci.yml"},
            {"id": 456, "workflow": "streamlit-validation.yml"},
        ]}}
        repairs = {"rerun_requests": 1, "decisions": [
            {"run_id": 123, "action": "rerun_requested", "reason": "HTTP 503"},
            {"run_id": 456, "action": "skip", "reason": "AssertionError"},
        ]}
        result = triage_code_failures(alerts, repairs)
        self.assertEqual(result[0]["auto_repair"], "ONE_FAILED_JOB_RETRY_REQUESTED")
        self.assertEqual(result[1]["auto_repair"], "DIAGNOSIS_ONLY_MANUAL_CODE_REVIEW")
        self.assertTrue(all(not p["code_changed"] for p in result))

    def test_source_status_matrix_is_fail_closed(self):
        for state in ("TECHNICAL_FAILURE", "CONFLICT", "REVIEW_REQUIRED", "UNAVAILABLE"):
            with self.subTest(state=state):
                result = classify(issue(state=state))
                self.assertTrue(result[2])
        self.assertEqual(classify(issue(state="CONFLICT"))[1],
                         "HOLD_CONFLICT_AND_RECHECK_PRIMARY")


if __name__ == "__main__":
    unittest.main()
