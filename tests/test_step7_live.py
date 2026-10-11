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
             "program_identity_status":"VERIFIED", "phase2_nct_ids":"NCT11112222"},
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

    def test_phase3_registry_primary_p_is_displayed_but_not_success(self):
        table(self.root, "phase3_primary_pvalues.csv", [
            {"ticker":"ABC", "nct_id":"NCT12345678",
             "source_url":"https://clinicaltrials.gov/study/NCT12345678",
             "p_value":"0.002","effect_value":"-1.9","ci_lower":"-2.4","ci_upper":"-1.1",
             "result_posted_at":"2026-10-09","checked_at":self.recent,"drug":"Drug A"},
            {"ticker":"ABC", "nct_id":"NCT87654321",
             "source_url":"https://clinicaltrials.gov/study/NCT87654321",
             "p_value":"0.0001","effect_value":"","ci_lower":"","ci_upper":"",
             "result_posted_at":"2026-10-09","checked_at":self.recent,"drug":"Drug B"},
        ])
        trials, _, _ = build_snapshot(self.root, NOW)
        a = next(x for x in trials if x["Ticker"] == "ABC")
        b = next(x for x in trials if x["Ticker"] == "XYZ")
        self.assertEqual(a["Primary endpoint p values observed"], "0.002")
        self.assertEqual(b["Primary endpoint p values observed"], "")
        self.assertIn("REVIEW", a["Phase 3 result interpretation"])
        self.assertTrue(a["ENTRY READY"].startswith("NO"))

    def test_linked_phase2_primary_p_is_source_dated_and_not_phase3_success(self):
        table(self.root, "phase2_primary_p_evidence.csv", [
            {"ticker":"ABC", "nct_id":"NCT11112222", "observation_id":"a",
             "p_value":"0.012", "primary_endpoint":"Symptom change",
             "comparison":"active vs placebo",
             "results_first_posted":"2026-09-01",
             "observed_at_utc":self.recent,
             "source_url":"https://clinicaltrials.gov/study/NCT11112222"},
            {"ticker":"XYZ", "nct_id":"NCT11112222", "observation_id":"b",
             "p_value":"0.0001", "primary_endpoint":"Other effect",
             "comparison":"active vs placebo",
             "results_first_posted":"2026-09-01",
             "observed_at_utc":self.recent,
             "source_url":"https://clinicaltrials.gov/study/NCT11112222"},
        ])
        trials, _, state = build_snapshot(self.root, NOW)
        abc = next(r for r in trials if r["Ticker"] == "ABC")
        xyz = next(r for r in trials if r["Ticker"] == "XYZ")
        self.assertIn("p=0.012", abc["Linked Phase 2 PRIMARY p"])
        self.assertEqual(abc["Phase 2 PRIMARY evidence count"], 1)
        self.assertEqual(xyz["Phase 2 PRIMARY evidence count"], 0)
        self.assertEqual(abc["Issuer Phase 3 readout"], "NOT VERIFIED HERE")
        self.assertIn("NO", abc["ENTRY READY"])
        later, _, _ = build_snapshot(self.root, NOW - timedelta(days=1))
        other = next(r for r in later if r["Ticker"] == "ABC")
        self.assertEqual(other["Phase 2 PRIMARY evidence count"], 0)

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

    def test_resolved_fda_event_excluded_from_proposed_trades(self):
        table(self.root, "pdufa_candidates.csv", [
            {"event_key":"ABC|DRUGA_20261231", "pdufa_date":"2026-12-31",
             "outcome":"APPROVED", "check_status":"RESOLVED_APPROVED",
             "monitor_eligibility":"EXCLUDED", "phase3_status":"RESULTS_REVIEW",
             "new_dilution_flag":"UNKNOWN"}
        ])
        _, finance, state = build_snapshot(self.root, NOW)
        self.assertTrue(finance[0]["Proposed trade status"].startswith("EXCLUDED"))
        self.assertIn("FDA decision already recorded", finance[0]["Gate reasons"])
        self.assertEqual(state["entry_ready_count"], 0)

    def test_quote_becomes_stale_after_session_and_collector_age(self):
        table(self.root, "step7_market_status.csv", [
            {"ticker":"ABC","checked_at_utc":self.recent,
             "last_session":"2026-10-09","last_close_usd":"25",
             "last_session_freshness":"RECENT EOD",
             "market_status":"MARKET_UPDATED","relative_volume":"1.1",
             "market_source":"https://query1.finance.yahoo.com/v8/finance/chart/ABC"}
        ])
        _, finance, _ = build_snapshot(self.root, NOW)
        self.assertEqual(finance[0]["Last EOD close USD"], "25")
        _, late, _ = build_snapshot(self.root, NOW + timedelta(days=8))
        self.assertEqual(late[0]["Last EOD close USD"], "")
        self.assertIn("RECHECK REQUIRED", late[0]["Price feed quality"])

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
