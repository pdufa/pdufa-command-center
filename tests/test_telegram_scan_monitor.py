import unittest
from scripts.telegram_scan_monitor import changes, is_active_scan
from scripts.telegram_scan_alert import message


def run(id=100, status="in_progress", conclusion=None, path=".github/workflows/pdufa-individual-clinical-scan.yml", event="workflow_dispatch", title="PDUFA Individual Clinical Scan"):
    return {"id": id, "run_attempt": 1, "status": status, "conclusion": conclusion, "path": path,
            "event": event, "name": title, "display_title": title, "html_url": f"https://github.com/pdufa/pdufa-command-center/actions/runs/{id}",
            "created_at": "2026-11-05T00:00:00Z", "updated_at": "2026-11-05T00:01:00Z"}


class TestTelegramScanMonitor(unittest.TestCase):
    def test_first_poll_seeds_without_spamming(self):
        events, state = changes([run()], {}, initializing=True)
        self.assertEqual(events, [])
        self.assertTrue(state["100:1"]["started"])

    def test_manual_start_and_end_once(self):
        events, state = changes([run()], {}, initializing=False)
        self.assertEqual([kind for kind, _ in events], ["scan-start"])
        events, state = changes([run(id=100, status="completed", conclusion="success")], state)
        self.assertEqual([kind for kind, _ in events], ["scan-end"])
        events, state = changes([run(id=100, status="completed", conclusion="success")], state)
        self.assertEqual(events, [])

    def test_completion_before_first_seen(self):
        events, _ = changes([run(status="completed", conclusion="failure")], {}, initializing=False)
        self.assertEqual([kind for kind, _ in events], ["scan-end"])
        self.assertIn("FAILED / INCOMPLETE", message("scan-end", "failure"))

    def test_not_legacy_or_own_monitor_or_push_ci(self):
        self.assertFalse(is_active_scan(run(title="GEM JR research", path=".github/workflows/pdufa-individual-clinical-scan.yml")))
        self.assertFalse(is_active_scan(run(path=".github/workflows/gem-research-quality.yml", title="GEM")))
        self.assertFalse(is_active_scan(run(path=".github/workflows/pdufa-telegram-24x7.yml")))
        self.assertFalse(is_active_scan(run(event="pull_request")))
        self.assertFalse(is_active_scan(run(event="push")))

    def test_raas_manual_research_and_daytime_scan(self):
        self.assertTrue(is_active_scan(run(path=".github/workflows/raas-evidence-snapshot-capture.yml", title="RAAS evidence snapshot capture")))
        self.assertTrue(is_active_scan(run(path=".github/workflows/pdufa-filings-section-scan.yml", title="FDA source scan")))

    def test_existing_direct_alerts_not_duplicated(self):
        self.assertFalse(is_active_scan(run(path=".github/workflows/pdufa-overnight-sequential.yml")))
        self.assertFalse(is_active_scan(run(path=".github/workflows/raas-fda-decision-accuracy.yml")))

if __name__ == "__main__":
    unittest.main()
