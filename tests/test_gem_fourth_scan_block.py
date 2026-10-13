"""Fourth GEMS scan block: exact selection, report integrity and no-trade guarantees."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from gem_scan_block_ui import valid_gem_report, gem_block_summary_row, report_recent
from scripts.publish_gem_scan_block import make_block_report, dict_json
from scripts.scan_email import compose_start, compose_end, label


class GemsFourthBlockTests(unittest.TestCase):
    def readiness(self):
        return {
            "acceptance_checks": {
                "phase3_discovery_ledger_reconciled": True,
                "sec_financing_source_current": False,
                "historical_return_edge_independently_validated": False,
            },
            "phase3_saved_ledger_rows": 2482,
            "verified_phase3_tracking": 3,
            "awaiting_second_financing": 3,
            "strict_entry_gate_shortlist_count": 0,
            "ranked": {"Phase 3": 8, "Post-Financing": 0, "PDUFA": 0},
            "research_status": "RESEARCH_ONLY_RANKING_NOT_RETURN_VALIDATED",
            "blocking_or_review_flags": ["SEC_FINANCING_COVERAGE_BLOCKED_OR_STALE"],
            "sec_source_health": {"status": "PARTIAL_STALE_OR_BLOCKED"},
            "market_source_health": {"status": "CURRENT_SOURCE_ONLY"},
        }

    def clinical(self):
        return {
            "complete": True, "status": "COMPLETE",
            "studies_checked": 3973, "matched_posted_results": 98,
            "new_records": 4, "stored_results": 2482,
            "finished_at": "2026-10-13T21:20:08+00:00",
        }

    def block(self, action="REVERIFY_PARTIAL", *, collector="success", audit="success",
              readiness=None, clinical=None):
        return make_block_report(
            self.readiness() if readiness is None else readiness,
            self.clinical() if clinical is None else clinical,
            action=action, collector_outcome=collector,
            audit_outcome=audit, run_id="38470000000",
            timestamp="2026-10-13T21:30:00Z",
        )

    def test_fourth_block_is_distinct_from_existing_post3_scan_four(self):
        self.assertEqual(label("4"), "#4 POST3")
        self.assertEqual(label("GEM"), "BLOCK 4 — GEMS")
        self.assertEqual(self.block()["scan"], "GEM")
        at = datetime(2026, 10, 13, tzinfo=timezone.utc)
        subject, body = compose_start("GEM", "DELTA", "run-test", at)
        self.assertIn("START - BLOCK 4 — GEMS", subject)
        self.assertIn("Run ID: run-test", body)
        end_subject, end_body = compose_end("GEM", "DELTA", "run-test", at,
                                            "PARTIAL", "source-gated", 300)
        self.assertIn("END - BLOCK 4 — GEMS", end_subject)
        self.assertIn("PARTIAL", end_subject)
        self.assertIn("source-gated", end_body)

    def test_completed_collector_is_not_verified_financing_or_trade_approval(self):
        item = self.block()
        self.assertEqual(item["schema_version"], 1)
        self.assertTrue(valid_gem_report(item))
        self.assertEqual(item["status"], "PARTIAL")
        self.assertTrue(item["collector_performed"])
        self.assertEqual(item["clinical_registry"]["new_records"], 4)
        self.assertEqual(item["clinical_registry"]["stored_results"], 2482)
        self.assertEqual(item["ranked_research_only"]["Phase 3"], 8)
        self.assertEqual(item["strict_entry_gate_shortlist_count"], 0)
        self.assertFalse(item["trade_entry_authorized"])
        self.assertFalse(item["historical_return_edge_validated"])
        self.assertFalse(item["full_universe_coverage_verified"])
        self.assertIn("SEC_FINANCING_COVERAGE_BLOCKED_OR_STALE",
                      item["blocking_or_review_flags"])
        self.assertEqual(gem_block_summary_row(item)["New records"], 4)
        self.assertEqual(gem_block_summary_row(item)["Changed trials"], None)
        self.assertEqual(gem_block_summary_row(item)["Scan"], "BLOCK 4 — GEMS")

    def test_verify_only_never_invents_collection_or_new_results(self):
        item = self.block("VERIFY_ALL", collector="skipped")
        self.assertEqual(item["status"], "PARTIAL")
        self.assertFalse(item["collector_performed"])
        self.assertIsNone(item["clinical_registry"]["new_records"])
        self.assertIsNone(item["clinical_registry"]["studies_checked"])
        self.assertIsNone(item["clinical_registry"]["stored_results"])
        self.assertEqual(item["observed_phase3_rows"], 2482)
        self.assertIn("NOT_RUN", item["collector_status"])

    def test_failed_collector_does_not_use_old_record_count_as_current(self):
        item = self.block(collector="failure")
        self.assertEqual(item["status"], "FAILED")
        self.assertIsNone(item["clinical_registry"]["stored_results"])
        self.assertIsNone(item["clinical_registry"]["new_records"])
        self.assertTrue(item["errors"])
        self.assertTrue(valid_gem_report(item))

    def test_partial_collector_and_audit_failure_are_fail_closed(self):
        item = self.block(clinical={**self.clinical(), "complete": False})
        self.assertEqual(item["status"], "FAILED")
        item = self.block(audit="failure")
        self.assertEqual(item["status"], "FAILED")
        self.assertIsNone(item["verified_phase3_tracking"])
        self.assertFalse(item["trade_entry_authorized"])

    def test_mismatched_registry_count_cannot_publish_complete_status(self):
        item = self.block(clinical={**self.clinical(), "stored_results": 2491})
        self.assertEqual(item["status"], "FAILED")
        self.assertTrue(any("disagree" in err for err in item["errors"]))

    def test_invalid_or_malicious_report_does_not_display(self):
        item = self.block()
        for change in (
            {"scan": "4"},
            {"schema_version": 9},
            {"status": "COMPLETE"},
            {"trade_entry_authorized": True},
            {"clinical_registry": None},
        ):
            self.assertFalse(valid_gem_report({**item, **change}))
        self.assertIsNone(gem_block_summary_row({})["New records"])
        self.assertEqual(gem_block_summary_row({})["Overall coverage"], "UNVERIFIED")
        self.assertTrue(report_recent(item, now=datetime(2026, 10, 13, 21, 31, tzinfo=timezone.utc)))
        self.assertFalse(report_recent(item, now=datetime(2026, 10, 17, tzinfo=timezone.utc)))

    def test_gems_workflow_and_nightly_controls_are_wired_as_fourth_block(self):
        root = Path(__file__).resolve().parents[1]
        nightly = (root / "nightly_scan_dashboard.py").read_text(encoding="utf-8")
        control = (root / ".github/workflows/pdufa-scan-control.yml").read_text(encoding="utf-8")
        workflow = (root / ".github/workflows/gem-research-quality.yml").read_text(encoding="utf-8")
        self.assertIn('"GEM": "BLOCK 4 — GEMS"', nightly)
        self.assertIn('options=["2", "3", "4", "GEM"]', nightly)
        self.assertIn('rows.append(gem_block_summary_row(gem_report))', nightly)
        self.assertIn('render_gem_scan_block_status(gem_report, gem_running)', nightly)
        self.assertIn('VERIFY SAVED SOURCES', nightly)
        self.assertIn('RESCAN SELECTED', nightly)
        self.assertIn("options: [ALL, '2', '3', '4', GEM]", control)
        self.assertIn("gem-research-quality.yml/dispatches", control)
        self.assertIn('scan = os.environ["CONTROL_SCAN"]', control)
        self.assertIn('action not in ("VERIFY_ALL", "REVERIFY_PARTIAL", "RESCAN_ALL")', control)
        self.assertIn("Gmail START — GEM block", workflow)
        self.assertIn("Gmail END — GEM block", workflow)
        self.assertIn("options: [VERIFY_ALL, REVERIFY_PARTIAL, RESCAN_ALL]", workflow)
        self.assertIn("RESCAN_ALL", workflow)
        self.assertIn("phase3_results_intake.py --mode backfill", workflow)
        self.assertIn("phase3_results_intake.py --mode daily", workflow)
        self.assertIn('if [ "$GEM_ACTION" != "VERIFY_ALL" ]', workflow)
        self.assertIn("git add -- data/gem_scan_block_report.json", workflow)
        self.assertIn("git add -- data/phase3_intake_status.json data/phase3_announcements.csv", workflow)

    def test_unreadable_report_file_cannot_be_mistaken_for_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            path.write_text('{"status": "COMPLETE",', encoding="utf-8")
            self.assertEqual(dict_json(path), {})


if __name__ == "__main__":
    unittest.main()
