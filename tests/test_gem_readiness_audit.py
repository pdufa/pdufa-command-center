"""Readiness, historical-data honesty and prospective research regression."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_readiness_audit import (
    build_readiness_report, clinical_collection_status, csv_inventory,
    json_inventory, source_family_health,
)
from gem_prospective import build_observations, observations_csv
from gem_scans import STAGES, build_gem_scans


TODAY = date(2026, 10, 13)


def fixture():
    item = {
        "Ticker": "TEST", "NCT ID": "NCT01234567",
        "Exact event": "TEST|PROGRAM_20261231",
        "Drug": "Program A",
        "As of Pacific": TODAY.isoformat(),
        "Phase 3 tracking": "TRACKING — VERIFIED SUCCESSFUL PHASE 3",
        "Financing watch": "SECOND FINANCING NOT VERIFIED CLOSED — MONITOR",
        "2nd Financing Completed": "NOT VERIFIED",
        "PDUFA date": "2026-12-31", "Days to PDUFA": 79,
        "Phase 3 source": "https://issuer.example/phase3",
        "Financing source": "", "PDUFA source": "https://issuer.example/pdufa",
    }
    for stage in STAGES:
        item[stage+" score"] = None
        item[stage+" rank"] = None
        item[stage+" qualifier"] = "REVIEW — NOT QUALIFIED"
    item["Phase 3 score"] = 85
    item["Phase 3 rank"] = 1
    item["Phase 3 qualifier"] = "QUALIFIED — RESEARCH ONLY"
    return item


class GemReadinessTests(unittest.TestCase):
    def test_empty_historical_evidence_cannot_be_called_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("gem_historical_snapshots.csv",
                         "post_phase3_historical_adjusted_ohlcv.csv"):
                (root / name).write_text("event_key,ticker\n", encoding="utf-8")
            item = fixture()
            report = build_readiness_report(
                root, [item], {"feed_current": False}, [], {}, as_of=TODAY
            )
            self.assertFalse(report["historical_return_edge_validated"])
            self.assertFalse(report["full_universe_coverage_verified"])
            self.assertFalse(report["automated_trading_enabled"])
            self.assertEqual(report["research_status"],
                             "HOLD_STALE_OR_MISSING_SOURCES")
            self.assertIn("UNVALIDATED_HISTORICAL_STOCK_RETURNS",
                          report["blocking_or_review_flags"])
            self.assertEqual(report["verified_phase3_tracking"], 1)
            self.assertEqual(report["awaiting_second_financing"], 1)

    def test_phase3_collector_count_mismatch_blocks_research_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"phase3_announcements.csv").write_text(
                "ticker,nct_id\nTEST,NCT01234567\n", encoding="utf-8"
            )
            (root/"phase3_intake_status.json").write_text(json.dumps({
                "status": "COMPLETE", "complete": True,
                "finished_at": "2026-10-13T16:00:00Z",
                "stored_results": 2482,
            }), encoding="utf-8")
            report = build_readiness_report(
                root, [], {"feed_current": True}, [], {}, as_of=TODAY
            )
            self.assertFalse(report["phase3_saved_ledger_reconciled"])
            self.assertEqual(report["phase3_saved_ledger_rows"], 1)
            self.assertEqual(report["phase3_collector_reported_stored_rows"], 2482)
            self.assertIn("PHASE3_RESULT_LEDGER_MISSING_OR_COUNT_MISMATCH",
                          report["blocking_or_review_flags"])
            self.assertFalse(report["all_acceptance_checks_passed"])
            self.assertFalse(report["acceptance_checks"]["phase3_discovery_ledger_reconciled"])

    def test_valid_source_row_counts_reconcile_without_certifying_return_edge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"phase3_announcements.csv").write_text(
                "ticker,nct_id\nTEST,NCT01234567\n", encoding="utf-8"
            )
            (root/"phase3_intake_status.json").write_text(json.dumps({
                "status": "COMPLETE", "complete": True,
                "finished_at": "2026-10-13T16:00:00Z",
                "stored_results": 1,
            }), encoding="utf-8")
            report = build_readiness_report(
                root, [], {"feed_current": True}, [], {}, as_of=TODAY
            )
            self.assertTrue(report["phase3_saved_ledger_reconciled"])
            self.assertFalse(report["historical_return_edge_validated"])
            self.assertFalse(report["all_acceptance_checks_passed"])
            self.assertEqual(len(report["acceptance_checks"]), 9)

    def test_stale_and_blocked_sec_checks_cannot_be_counted_as_healthy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            status_path = root/"step7_live_status.json"
            status_path.write_text(json.dumps({"source_checks":[{
                "Source":"SEC financing recheck",
                "Collector status":"COMPLETE",
                "Freshness":"RECENT",
                "Blocked records":38,
                "Last checked UTC":"2026-10-13T16:00:00Z"
            }]}), encoding="utf-8")
            self.assertEqual(source_family_health(
                status_path, "SEC financing recheck", TODAY)["status"],
                "PARTIAL_STALE_OR_BLOCKED")
            status_path.write_text(json.dumps({"source_checks":[{
                "Source":"SEC financing recheck",
                "Collector status":"COMPLETE",
                "Freshness":"RECENT",
                "Blocked records":0,
                "Last checked UTC":"2026-10-13T16:00:00Z"
            }]}), encoding="utf-8")
            self.assertEqual(source_family_health(
                status_path, "SEC financing recheck", TODAY)["status"],
                "CURRENT_SOURCE_ONLY")

    def test_invalid_json_input_is_not_marked_present(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"step7_live_status.json"
            path.write_text("{bad json", encoding="utf-8")
            self.assertEqual(json_inventory(path)["state"], "INVALID_JSON")

    def test_csv_inventory_rejects_duplicate_header_and_malformed_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"source.csv"
            path.write_text("ticker,ticker\nTEST,TEST\n", encoding="utf-8")
            self.assertEqual(csv_inventory(path)["state"], "INVALID_HEADER")
            path.write_text("ticker,nct\nTEST,NCT01234567,EXTRA\n",
                            encoding="utf-8")
            self.assertEqual(csv_inventory(path)["state"], "MALFORMED_ROW")
            path.write_text("ticker,nct\nTEST,NCT01234567\n",
                            encoding="utf-8")
            self.assertEqual(csv_inventory(path)["rows"], 1)

    def test_collector_requires_actual_completed_dated_result(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"phase3_intake_status.json"
            path.write_text(json.dumps({
                "status": "COMPLETE", "complete": True,
                "finished_at": "2026-10-13T16:00:00Z",
            }), encoding="utf-8")
            self.assertEqual(clinical_collection_status(path, TODAY)["status"],
                             "CURRENT_CLINICAL_ONLY")
            path.write_text(json.dumps({
                "status": "PARTIAL", "complete": False,
                "finished_at": "2026-10-13T16:00:00Z",
            }), encoding="utf-8")
            self.assertEqual(clinical_collection_status(path, TODAY)["status"],
                             "PARTIAL_SOURCE_CHECK")

    def test_prospective_dated_rows_cannot_become_historical_training(self):
        rows = build_observations(
            [fixture()], {"feed_current": True}, as_of=TODAY
        )
        self.assertEqual(len(rows), len(STAGES))
        p3 = next(r for r in rows if r["stage"] == "Phase 3")
        self.assertEqual(p3["gem_score"], 85)
        self.assertEqual(p3["gem_rank"], 1)
        self.assertEqual(p3["training_eligible"],
                         "NO — NOT HISTORICAL TRADE VERIFIED")
        self.assertEqual(p3["realized_return_known"], "NO")
        self.assertIn("observation_id", observations_csv(rows))

    def test_stale_source_never_produces_a_qualified_prospective_score(self):
        rows = build_observations(
            [fixture()], {"feed_current": False}, as_of=TODAY
        )
        self.assertEqual(len(rows), len(STAGES))
        self.assertTrue(all(r["gem_score"] is None and
                            r["research_qualification"] == "SOURCE_HOLD"
                            for r in rows))

    def test_duplicate_program_must_not_be_silently_averaged(self):
        with self.assertRaisesRegex(ValueError, "Duplicate exact-event"):
            build_observations(
                [fixture(), fixture()], {"feed_current": True}, as_of=TODAY
            )

    def test_future_dated_verified_phase3_is_not_activated(self):
        row = fixture()
        row.update({
            "Entry qualification": "REVIEW — ENTRY BLOCKED",
            "Phase 3 evidence": "VERIFIED SUCCESS — SOURCE LINKED",
            "Trading setup /20": 20,
            "Clinical evidence /30": 30,
            "Market activity /10": 10,
            "Evidence score /100": 80,
        })
        event = {
            row["Exact event"]: {
                "ticker": "TEST", "nct_id": "NCT01234567",
                "phase3_status": "VERIFIED_SUCCESS",
                "phase3_date": "2026-10-15",
                "trial_evidence_url": "https://issuer.example/result",
                "conflict_flag": "NONE",
                "new_dilution_flag": "NO",
            }
        }
        with patch("gem_scans.build_queue", return_value=(
            [row], {"feed_current": True, "as_of": TODAY.isoformat()}
        )), patch("gem_scans._event_map", return_value=event):
            scored, meta = build_gem_scans("fake")
        self.assertTrue(scored[0]["Phase 3 tracking"].startswith("AWAITING"))
        self.assertEqual(meta["phase3_tracking_count"], 0)

    def test_conflicting_trial_identity_not_activated(self):
        row = fixture()
        row.update({
            "Entry qualification": "REVIEW — ENTRY BLOCKED",
            "Phase 3 evidence": "VERIFIED SUCCESS — SOURCE LINKED",
        })
        event = {
            row["Exact event"]: {
                "ticker": "TEST", "nct_id": "NCT99999999",
                "phase3_status": "VERIFIED_SUCCESS",
                "phase3_date": "2026-09-15",
                "trial_evidence_url": "https://issuer.example/result",
                "conflict_flag": "NONE",
            }
        }
        with patch("gem_scans.build_queue", return_value=(
            [row], {"feed_current": True, "as_of": TODAY.isoformat()}
        )), patch("gem_scans._event_map", return_value=event):
            scored, meta = build_gem_scans("fake")
        self.assertIn("IDENTITY CONFLICT", scored[0]["Phase 3 tracking"])
        self.assertEqual(meta["phase3_tracking_count"], 0)

    def test_offline_daily_archival_workflow_has_no_brokerage_action(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root/".github/workflows/gem-research-quality.yml").read_text()
        # GEM is an awaited reusable step in the 9 PM Pacific serial chain,
        # not a second independently scheduled collector.
        self.assertIn("workflow_call:", workflow)
        self.assertNotIn("  schedule:", workflow)
        clinical = (root/".github/workflows/pdufa-nightly-clinical.yml").read_text()
        self.assertIn("uses: ./.github/workflows/gem-research-quality.yml", clinical)
        self.assertIn("needs: scan4", clinical)
        self.assertIn("needs: gem_block", clinical)

        self.assertIn("contents: write", workflow)
        self.assertIn("--mode backfill", workflow)
        self.assertIn("--mode daily", workflow)
        self.assertIn("phase3_results_intake.py", workflow)
        self.assertIn("stored_results", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
        # Publish PARTIAL/FAILED block visibility even on collector errors,
        # but the clinical ledger must only publish after exact count validation.
        self.assertIn("if: always()", workflow)
        self.assertIn("steps.registry_validation.outcome", workflow)
        self.assertIn("git add -- data/gem_scan_block_report.json", workflow)
        self.assertIn("git add -- data/phase3_intake_status.json data/phase3_announcements.csv", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertIn("run_gem_daily_readiness.py", workflow)
        self.assertIn("research-only", (root/"gem_prospective.py").read_text().lower())


if __name__ == "__main__":
    unittest.main()
