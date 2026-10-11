"""Fail-closed Step 7 synthetic regression tests; no external calls."""
import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from step7_live import build_snapshot, freshness, timestamp


NOW = datetime(2026, 10, 10, 18, tzinfo=timezone.utc)


def table(root, name, rows):
    with (root / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class Step7Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.recent = (NOW - timedelta(hours=1)).isoformat()
        self.stale = (NOW - timedelta(days=7)).isoformat()
        table(self.root, "phase_pipeline.csv", [
            {"ticker":"ABC", "nct_id":"NCT12345678", "phases":"PHASE3",
             "trial_status":"RECRUITING", "drug":"Drug A", "indication":"Disease A",
             "results_first_posted":"", "checked_at":self.recent,
             "primary_completion":"2026-12", "source_url":"https://clinicaltrials.gov/study/NCT12345678",
             "program_identity_status":"VERIFIED"},
            {"ticker":"XYZ", "nct_id":"NCT87654321", "phases":"PHASE2",
             "trial_status":"RECRUITING", "drug":"Drug B", "indication":"Disease B",
             "results_first_posted":"2026-09-15", "checked_at":self.recent,
             "primary_completion":"2027-02", "source_url":"https://clinicaltrials.gov/study/NCT87654321"},
        ])
        table(self.root, "pre_readout_protocols.csv", [
            {"nct_id":"NCT12345678", "checked_at":self.recent, "source_url":"https://clinicaltrials.gov/study/NCT12345678"}
        ])
        table(self.root, "phase_pipeline_market_caps.csv", [
            {"ticker":"ABC", "market_cap":"500000000", "market_cap_status":"VERIFIED",
             "market_cap_source":"https://api.nasdaq.com/api/quote/ABC/summary",
             "market_cap_checked_at":self.recent},
            {"ticker":"XYZ", "market_cap":"1000000000", "market_cap_status":"VERIFIED",
             "market_cap_source":"https://api.nasdaq.com/api/quote/XYZ/summary",
             "market_cap_checked_at":self.stale},
        ])
        table(self.root, "second_financing_status.csv", [
            {"event_key":"ABC|DRUGA_20261231",
             "second_financing_closed":"YES", "second_financing_audit_status":"VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_financing_date":"2026-07-01", "second_financing_date":"2026-09-01",
             "first_financing_source":"https://www.sec.gov/first",
             "second_financing_source":"https://www.sec.gov/second"}
        ])
        table(self.root, "recheck_status.csv", [
            {"event_key":"ABC|DRUGA_20261231", "financing_status":"SOURCE_BLOCKED_RETAINED",
             "completed_at_utc":self.recent}
        ])
        for name, dt in [
            ("phase_pipeline_state.json", {"status":"COMPLETE WITH WARNINGS","finished_at":self.recent}),
            ("phase3_intake_status.json", {"status":"COMPLETE","finished_at":self.recent,"stored_results":3}),
            ("pre_readout_intake_status.json", {"status":"COMPLETE","as_of":self.recent}),
        ]:
            (self.root / name).write_text(json.dumps(dt), encoding="utf-8")

    def test_latest_trial_market_and_financing_fail_closed(self):
        trials, finances, state = build_snapshot(self.root, NOW)
        self.assertEqual(len(trials), 2)
        a = next(r for r in trials if r["Ticker"] == "ABC")
        self.assertEqual(a["Market cap USD"], 500000000.0)
        self.assertEqual(a["Protocol check"], "RECENT")
        self.assertIn("NO —", a["ENTRY READY"])
        b = next(r for r in trials if r["Ticker"] == "XYZ")
        self.assertEqual(b["Market cap state"], "STALE")
        self.assertIsNone(b["Market cap USD"])
        self.assertEqual(state["entry_ready_count"], 0)
        self.assertEqual(len(finances), 1)
        self.assertEqual(finances[0]["Recheck freshness"], "RECENT")
        self.assertEqual(finances[0]["Current gate"].split(" — ")[0], "REVIEW")
        self.assertEqual(finances[0]["Why blocked"], "SEC recheck blocked or missing; historical sources retained")
        self.assertTrue(any(r["Source"] == "SEC financing recheck" and r["Health"] == "BLOCKED / PARTIAL"
                            for r in state["source_checks"]))

    def test_no_ticker_only_protocol_or_market_match(self):
        trials, _, _ = build_snapshot(self.root, NOW)
        r = next(r for r in trials if r["NCT ID"] == "NCT87654321")
        self.assertEqual(r["Protocol check"], "NOT REQUIRED FOR PHASE 2 WATCH")
        self.assertEqual(r["Market cap state"], "STALE")

    def test_bad_dates_are_not_fresh(self):
        self.assertEqual(freshness("", NOW, 24), "NO TIMESTAMP")
        self.assertEqual(freshness("2028-01-01", NOW, 24), "INVALID FUTURE TIMESTAMP")
        self.assertIsNone(timestamp("not-a-date"))

    def test_registry_result_does_not_prove_positive_phase3(self):
        trials, _, _ = build_snapshot(self.root, NOW)
        b = next(r for r in trials if r["Ticker"] == "XYZ")
        self.assertEqual(b["Research category"], "RESULT POSTED — CLINICAL REVIEW")
        self.assertEqual(b["Issuer Phase 3 readout"], "NOT VERIFIED HERE")
        self.assertTrue(b["ENTRY READY"].startswith("NO"))

    def test_invalid_closure_evidence_never_promotes_trade(self):
        table(self.root, "second_financing_status.csv", [
            {"event_key":"ABC|DRUGA_20261231", "second_financing_closed":"YES",
             "second_financing_audit_status":"VERIFIED_SECOND_POST_PHASE3_FINANCING",
             "first_financing_date":"2026-07-01", "second_financing_date":"2026-09-01",
             "first_financing_source":"", "second_financing_source":"not-a-sec-url"},
        ])
        _, finance, state = build_snapshot(self.root, NOW)
        self.assertEqual(finance[0]["Historical second closing"], "NOT VERIFIED")
        self.assertEqual(state["entry_ready_count"], 0)


if __name__ == "__main__":
    unittest.main()
