"""No GEM trade-entry review is possible before verified close #2."""
from datetime import date, timedelta
import json
import tempfile
from pathlib import Path
import unittest

from gem_financing_gate import second_post_phase3_close, entry_status, sec_recheck_current

EVENT = "ACME|PHASE3_20261201"
AS_OF = date(2026, 10, 13)


def closed(**overrides):
    row = {
        "event_key": EVENT,
        "second_financing_status": "CLOSED",
        "second_financing_closed": "YES",
        "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
        "first_financing_date": "2026-02-01",
        "first_financing_source": "https://www.sec.gov/Archives/edgar/data/11/first",
        "second_financing_date": "2026-07-09",
        "second_financing_source": "https://www.sec.gov/Archives/edgar/data/11/second",
        "verified_as_of": AS_OF.isoformat(),
    }
    row.update(overrides)
    return row


class GemAbsoluteEntryTests(unittest.TestCase):
    def test_two_distinct_verified_closes_required(self):
        verified, close_date, reason = second_post_phase3_close(
            EVENT, "2026-01-10", closed(), as_of=AS_OF
        )
        self.assertTrue(verified)
        self.assertEqual(close_date, "2026-07-09")
        self.assertEqual(reason, "")

    def test_announcement_pricing_in_progress_and_unverified_close_stay_watch_only(self):
        for state in ("ANNOUNCED", "PRICED", "RUNNING", "STARTED", ""):
            with self.subTest(state=state):
                valid, _, _ = second_post_phase3_close(
                    EVENT, "2026-01-10",
                    closed(second_financing_status=state), as_of=AS_OF
                )
                self.assertFalse(valid)
                self.assertEqual(entry_status(
                    closed=valid, qualified=True,
                    feed_current=True, days_to_pdufa=45
                ), "WATCH ONLY — SECOND FINANCING NOT VERIFIED CLOSED")

    def test_closure_attestation_not_sufficient_without_ordered_dates_and_sec(self):
        variants = (
            {"first_financing_date": ""},
            {"second_financing_date": ""},
            {"first_financing_date": "2025-12-01"},
            {"second_financing_date": "2026-02-01"},
            {"second_financing_date": "2026-11-01"},
            {"first_financing_source": ""},
            {"second_financing_source": "https://not-sec.example/close"},
            {"verified_as_of": "2026-10-01"},
            {"verified_as_of": "2026-10-14"},
            {"second_financing_audit_status": "CLOSED_REPORTED_ONLY"},
            {"second_financing_closed": "NO"},
            {"event_key": "OTHER|DRUG"},
        )
        for override in variants:
            with self.subTest(override=override):
                verified, _, reason = second_post_phase3_close(
                    EVENT, "2026-01-10", closed(**override), as_of=AS_OF
                )
                self.assertFalse(verified)
                self.assertTrue(reason)

    def test_stale_historical_close_survives_research_but_never_entry(self):
        historical = closed(verified_as_of="2026-09-28")
        recent, _, reason = second_post_phase3_close(
            EVENT, "2026-01-10", historical, as_of=AS_OF)
        self.assertFalse(recent)
        self.assertIn("STALE", reason)
        archived, close_date, note = second_post_phase3_close(
            EVENT, "2026-01-10", historical, as_of=AS_OF,
            require_fresh=False)
        self.assertTrue(archived)
        self.assertEqual(close_date, "2026-07-09")
        self.assertEqual(note, "")
        self.assertEqual(entry_status(
            closed=archived, qualified=True, feed_current=False,
            days_to_pdufa=60),
            "HOLD — STALE SOURCE EVIDENCE")
        future = closed(verified_as_of="2026-10-14")
        no_future, _, _ = second_post_phase3_close(
            EVENT, "2026-01-10", future, as_of=AS_OF,
            require_fresh=False)
        self.assertFalse(no_future)

    def test_post_close_is_manual_review_not_execution_or_guaranteed_entry(self):
        self.assertEqual(entry_status(
            closed=True, qualified=True,
            feed_current=True, days_to_pdufa=4
        ), "POST-CLOSE ENTRY REVIEW ELIGIBLE — NOT A TRADE ORDER")
        self.assertEqual(entry_status(
            closed=True, qualified=False,
            feed_current=True, days_to_pdufa=40
        ), "POST-CLOSE REVIEW — OTHER ENTRY GATES NOT MET")
        self.assertEqual(entry_status(
            closed=True, qualified=True,
            feed_current=False, days_to_pdufa=40
        ), "HOLD — STALE SOURCE EVIDENCE")
        self.assertEqual(entry_status(
            closed=True, qualified=True,
            feed_current=True, days_to_pdufa=3
        ), "NO NEW ENTRY — PDUFA −3 EXIT BOUNDARY")

    def test_sec_collector_requires_current_completed_unblocked_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "step7_live_status.json"
            row = {
                "Source": "SEC financing recheck",
                "Collector status": "COMPLETE",
                "Freshness": "RECENT",
                "Health": "RECENT",
                "Blocked records": 0,
                "Last checked UTC": "2026-10-13T16:00:00+00:00"
            }
            def set_status(source_rows):
                path.write_text(json.dumps({"source_checks": source_rows}),
                                encoding="utf-8")
            set_status([row])
            self.assertTrue(sec_recheck_current(directory, as_of=AS_OF))
            for override in (
                {"Blocked records": 1},
                {"Blocked records": None},
                {"Blocked records": "0"},
                {"Collector status": "PARTIAL"},
                {"Freshness": "STALE"},
                {"Health": "BLOCKED / PARTIAL"},
                {"Last checked UTC": "2026-10-01T16:00:00+00:00"},
                {"Last checked UTC": "2026-10-14T16:00:00+00:00"},
            ):
                with self.subTest(override=override):
                    set_status([{**row, **override}])
                    self.assertFalse(sec_recheck_current(directory, as_of=AS_OF))
            set_status([row, row])
            self.assertFalse(sec_recheck_current(directory, as_of=AS_OF))
            set_status([])
            self.assertFalse(sec_recheck_current(directory, as_of=AS_OF))

    def test_pre_close_rank_never_unlocks_entry(self):
        self.assertEqual(entry_status(
            closed=False, qualified=True,
            feed_current=True, days_to_pdufa=90
        ), "WATCH ONLY — SECOND FINANCING NOT VERIFIED CLOSED")


if __name__ == "__main__":
    unittest.main()
