"""Offline contracts for the SCANS live GitHub and evidence-health panel."""
import unittest

from scan_status_ui import (
    WORKFLOWS, pacific_time, run_link, run_state,
    verification_numbers, workflow_snapshots,
)


class ScanStatusPanelTests(unittest.TestCase):
    def test_progress_counts_only_resolved_mandatory_checks(self):
        result = verification_numbers({
            "required_findings_due": 984,
            "required_findings_unresolved": 82,
            "status": "PARTIAL",
        })
        self.assertEqual(result["resolved"], 902)
        self.assertEqual(result["remaining"], 82)
        self.assertAlmostEqual(result["percent"], 91.7)
        self.assertIsNone(verification_numbers({"required_findings_due": 0,
                                                "required_findings_unresolved": 0}))
        self.assertIsNone(verification_numbers({"status": "PARTIAL"}))

    def test_successful_execution_is_not_labeled_verified(self):
        self.assertEqual(run_state({"status": "completed", "conclusion": "success"}),
                         "FINISHED · success")
        self.assertEqual(run_state({"status": "completed", "conclusion": "failure"}), "FAILED")
        self.assertEqual(run_state({"status": "completed", "conclusion": "skipped"}), "SKIPPED")
        self.assertEqual(run_state({"status": "in_progress", "conclusion": None}), "RUNNING")
        self.assertEqual(run_state({"status": "queued", "conclusion": None}), "QUEUED")
        self.assertEqual(run_state({}), "UNKNOWN")

    def test_latest_important_workflows_ignore_unrelated_repair_noise(self):
        source = WORKFLOWS["FDA / SEC / Financial / Market / Issuer"]
        def run(name, number, created):
            return {"path": ".github/workflows/" + name, "id": number,
                    "created_at": created, "status": "completed"}
        data = [
            run(source, 8, "2026-10-13T15:20:00Z"),
            run("pdufa-safe-auto-repair.yml", 99, "2026-10-13T15:40:00Z"),
            run(source, 9, "2026-10-13T15:30:00Z"),
            run("ci.yml", 7, "2026-10-13T15:35:00Z"),
        ]
        found = workflow_snapshots(data)
        self.assertEqual(found[source]["id"], 9)
        self.assertEqual(found["ci.yml"]["id"], 7)
        self.assertNotIn("pdufa-safe-auto-repair.yml", found)

    def test_link_validation_rejects_other_repositories(self):
        self.assertEqual(
            run_link({"html_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/38425422351"}),
            "https://github.com/pdufa/pdufa-command-center/actions/runs/38425422351")
        self.assertEqual(run_link({"html_url": "https://github.com/attacker/fake/actions/runs/1"}), "")
        self.assertEqual(run_link({"html_url": "javascript:alert(1)"}), "")

    def test_pacific_time_and_missing_timestamp(self):
        self.assertIn("PDT", pacific_time("2026-10-13T15:50:03Z"))
        self.assertEqual(pacific_time(None), "—")
        self.assertEqual(pacific_time("broken"), "—")


if __name__ == "__main__":
    unittest.main()
