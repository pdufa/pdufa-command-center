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
            "updated_at_utc": "2026-10-14T07:30:00+00:00",
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
        clinical = {"updated_at_utc": "2026-10-14T07:00:00Z"}
        result = make_snapshot(clinical, {}, now=now)
        self.assertEqual(result["readiness"], "SOURCE_VERIFICATION_PENDING_OR_STALE")
        self.assertFalse(result["sources"]["overnight_report_published"])

    def test_fourth_gems_block_is_in_6am_result_only_when_same_night(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        gem = {
            "scan": "GEM", "schema_version": 1, "status": "PARTIAL",
            "trade_entry_authorized": False,
            "generated_at_utc": "2026-10-14T08:30:00Z",
            "collector_status": "COMPLETE — REGISTRY POSTINGS ONLY",
            "clinical_registry": {"new_records": 9, "stored_results": 2482},
            "verified_phase3_tracking": 4, "awaiting_second_financing": 3,
            "strict_entry_gate_shortlist_count": 0,
            "run_url": "https://github.com/pdufa/pdufa-command-center/actions/runs/123",
        }
        fresh = make_snapshot({}, {}, gem=gem, now=now)
        self.assertEqual(fresh["gem"]["status"], "PARTIAL")
        self.assertTrue(fresh["gem"]["overnight_report_published"])
        self.assertEqual(fresh["gem"]["new_records"], 9)
        self.assertEqual(fresh["gem"]["awaiting_second_financing"], 3)
        self.assertEqual(fresh["gem"]["strict_entry_gate_shortlist_count"], 0)
        self.assertEqual(fresh["gem"]["all_source_trade_verification"], "NOT VERIFIED")
        self.assertFalse(fresh["trade_entry_eligible_from_morning_snapshot"])
        old = make_snapshot({}, {}, gem={**gem, "generated_at_utc": "2026-10-13T19:10:00Z"}, now=now)
        self.assertFalse(old["gem"]["overnight_report_published"])
        self.assertEqual(old["gem"]["status"], "PENDING_OR_STALE")
        self.assertIsNone(old["gem"]["new_records"])
        self.assertIsNone(old["gem"]["stored_results"])
        self.assertIsNone(old["gem"]["strict_entry_gate_shortlist_count"])
        not_verified = make_snapshot({}, {}, gem={**gem, "trade_entry_authorized": True}, now=now)
        self.assertFalse(not_verified["gem"]["overnight_report_published"])

    def test_previous_night_after_11pm_publications_count_as_fresh(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        clinical = {"updated_at_utc": "2026-10-14T06:15:00Z"}
        source = {"updated_at_utc": "2026-10-14T07:15:00Z"}
        result = make_snapshot(clinical, source, now=now)
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS")
        self.assertEqual(result["overnight_scan_window_started_pacific"],
                         "2026-10-13T23:00:00-07:00")

    def test_previous_night_pre_11pm_remains_stale(self):
        now = datetime(2026, 10, 14, 13, 0, tzinfo=timezone.utc)
        old = {"updated_at_utc": "2026-10-14T05:59:00Z"}
        result = make_snapshot(old, old, now=now)
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PENDING_OR_STALE")

    def test_dst_standard_time_keeps_six_am_reporting(self):
        now = datetime(2026, 12, 14, 14, 0, tzinfo=timezone.utc)
        clinical = {"updated_at_utc": "2026-12-14T08:00:00Z"}
        source = {"updated_at_utc": "2026-12-14T09:30:00Z"}
        result = make_snapshot(clinical, source, now=now)
        self.assertEqual(result["snapshot_date_pacific"], "2026-12-14")
        self.assertEqual(result["overnight_scan_window_started_pacific"],
                         "2026-12-13T23:00:00-08:00")
        self.assertEqual(result["readiness"], "OVERNIGHT_REPORTS_PUBLISHED_WITH_EVIDENCE_GAPS")


if __name__ == "__main__":
    unittest.main()
