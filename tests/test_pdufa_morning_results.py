"""6 AM Pacific scan report must never label stale data as new."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.pdufa_morning_results import make_snapshot


class MorningResultsTests(unittest.TestCase):
    def test_fresh_night_has_percentage_but_not_trade_approval(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        clinical = {
            "updated_at_utc": "2026-10-14T04:30:00+00:00",
            "status": "PARTIAL",
            "scans": [{"scan": "4", "collector_status": "COMPLETE",
                       "new_records": 3, "changed_trials_this_execution": 2}],
        }
        source = {
            "updated_at_utc": "2026-10-14T09:00:00+00:00",
            "status": "PARTIAL",
            "required_findings_due": 985,
            "required_findings_unresolved": 45,
            "comparison": {"resolved_count": 2, "new_count": 2},
            "public_ir_sec_recheck": {"status": "COMPLETE_RESEARCH_ONLY",
                                      "leads_checked": 15,
                                      "sec_transactions_verified": 1},
        }
        result = make_snapshot(clinical, source, now=now)
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS")
        self.assertEqual(result["snapshot_date_pacific"], "2026-10-14")
        self.assertEqual(result["sources"]["required_source_coverage_percent"], 95.4)
        self.assertEqual(result["sources"]["sec_transactions_verified"], 1)
        self.assertFalse(result["trade_entry_eligible_from_morning_snapshot"])

    def test_old_sources_are_pending_not_certified(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        old = {"updated_at_utc": "2026-10-13T19:00:00Z",
               "required_findings_unresolved": 0,
               "required_findings_due": 100}
        result = make_snapshot(old, old, now=now)
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PENDING_OR_STALE")
        self.assertIsNone(result["sources"]["required_findings_unresolved"])
        self.assertIsNone(result["sources"]["required_source_coverage_percent"])

    def test_one_source_missing(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        clinical = {"updated_at_utc": "2026-10-14T05:00:00Z"}
        result = make_snapshot(clinical, {}, now=now)
        self.assertEqual(result["readiness"], "SOURCE_VERIFICATION_PENDING_OR_STALE")
        self.assertFalse(result["sources"]["overnight_report_published"])

    def test_dst_standard_time_keeps_six_am_reporting(self):
        now = datetime(2026, 12, 14, 14, 0, tzinfo=timezone.utc)
        clinical = {"updated_at_utc": "2026-12-14T08:00:00Z"}
        source = {"updated_at_utc": "2026-12-14T09:30:00Z"}
        result = make_snapshot(clinical, source, now=now)
        self.assertEqual(result["snapshot_date_pacific"], "2026-12-14")
        self.assertIn("-08:00", result["overnight_scan_window_started_pacific"])
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS")


if __name__ == "__main__":
    unittest.main()
