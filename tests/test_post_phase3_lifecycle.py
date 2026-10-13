"""Stage 2 lifecycle safety and edge cases (unittest discovery)."""
import unittest
from datetime import date, timedelta

from post_phase3_lifecycle import (
    JOURNAL_FIELDS, monitor_positions, parse_journal, template_csv,
)


TODAY = date(2026, 10, 11)
EVENT = "TEST|PROGRAM_20261115"
NCT = "NCT01234567"


def candidate(*, pdufa=35, verified=True, status="GREEN — GATES ATTESTED"):
    return {
        "Ticker": "TEST", "Exact event": EVENT, "NCT ID": NCT,
        "PDUFA date": (TODAY + timedelta(days=pdufa)).isoformat(),
        "PDUFA verification": "VERIFIED — SOURCE LINKED" if verified else "REVIEW",
        "Entry qualification": status,
    }


def trade(*, initial_pdufa=35, closed=False):
    return {
        "trade_id": "LOT-1", "event_key": EVENT, "ticker": "TEST",
        "nct_id": NCT,
        "entry_date": "2026-10-08", "entry_price": "10.00",
        "shares": "100", "pdufa_date_at_entry": (TODAY + timedelta(days=initial_pdufa)).isoformat(),
        "exit_date": "2026-10-10" if closed else "",
        "exit_price": "13.00" if closed else "",
        "exit_reason": "scheduled" if closed else "",
    }


def market(*, date_str="2026-10-09", price="12.00", checked="2026-10-11T14:00:00Z"):
    return [{
        "ticker": "TEST", "market_status": "MARKET_UPDATED",
        "last_session_freshness": "RECENT EOD",
        "last_session": date_str, "last_close_usd": price,
        "checked_at_utc": checked,
        "market_source": "https://query1.finance.yahoo.com/v8/finance/chart/TEST",
    }]


class TestPositionMonitoring(unittest.TestCase):
    def check(self, position=None, program=None, quote=None, date_value=TODAY):
        return monitor_positions(
            [trade() if position is None else position],
            [candidate() if program is None else program],
            market() if quote is None else quote,
            date_value,
        )

    def test_blank_queue_does_not_invent_positions(self):
        rows, totals = monitor_positions([], [candidate()], market(), TODAY)
        self.assertEqual(rows, [])
        self.assertEqual(totals["total"], 0)
        self.assertEqual(totals["open"], 0)

    def test_blank_template_is_header_only(self):
        raw = template_csv()
        self.assertEqual(parse_journal(raw), [])
        for col in JOURNAL_FIELDS:
            self.assertIn(col.encode(), raw)

    def test_parses_minimal_valid_position(self):
        content = template_csv().decode("utf-8-sig") + (
            "LOT-1,TEST|PROGRAM_20261115,TEST,NCT01234567,"
            "2026-10-08,10.00,100,2026-11-15,,,\n"
        )
        values = parse_journal(content.encode())
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["event_key"], EVENT)

    def test_rejects_wrong_header(self):
        with self.assertRaises(ValueError):
            parse_journal(b"trade_id,ticker\nT1,TEST\n")

    def test_rejects_extra_field(self):
        with self.assertRaises(ValueError):
            parse_journal(template_csv() + b"a,b,c,d,e,f,g,h,i,j,k,l\n")

    def test_rejects_large_upload(self):
        with self.assertRaises(ValueError):
            parse_journal(b"x" * 260_000)

    def test_no_brokerage_claims_on_open_trade(self):
        rows, totals = self.check()
        self.assertEqual(rows[0]["Trade lifecycle"], "YELLOW — OPEN / MONITOR")
        self.assertEqual(rows[0]["Marked or realized P/L %"], 20.0)
        self.assertEqual(rows[0]["Marked or realized P/L USD"], 200.0)
        self.assertEqual(totals["open"], 1)
        self.assertFalse(rows[0]["Exit date"])

    def test_exit_preparation_starts_seven_days_before_cutoff(self):
        rows, _ = self.check(position=trade(initial_pdufa=9),
                             program=candidate(pdufa=9))
        self.assertEqual(rows[0]["Trade lifecycle"], "YELLOW — EXIT PREPARATION")
        self.assertEqual(rows[0]["Days to exit deadline"], 5)

    def test_red_at_three_days_to_pdufa(self):
        rows, totals = self.check(position=trade(initial_pdufa=3),
                                  program=candidate(pdufa=3))
        self.assertEqual(rows[0]["Trade lifecycle"], "RED — EXIT DUE / NOT RECORDED")
        self.assertEqual(totals["due"], 1)
        self.assertLessEqual(rows[0]["Days to exit deadline"], 0)
        self.assertFalse(rows[0]["Exit date"])

    def test_closed_trade_only_from_user_report(self):
        rows, totals = self.check(position=trade(closed=True))
        self.assertEqual(rows[0]["Trade lifecycle"], "RED — EXIT RECORDED")
        self.assertEqual(rows[0]["Marked or realized P/L %"], 30.0)
        self.assertEqual(rows[0]["Marked or realized P/L USD"], 300.0)
        self.assertEqual(totals["recorded_exits"], 1)
        self.assertEqual(totals["open"], 0)

    def test_current_fda_resolved_requires_urgent_review(self):
        rows, totals = self.check(program=candidate(status="EXCLUDED — FDA DECIDED"))
        self.assertEqual(rows[0]["Trade lifecycle"], "RED — URGENT REGULATORY REVIEW")
        self.assertEqual(totals["due"], 1)

    def test_pdufa_change_uses_earlier_date(self):
        rows, totals = self.check(position=trade(initial_pdufa=3),
                                  program=candidate(pdufa=30))
        self.assertEqual(rows[0]["Trade lifecycle"], "RED — EXIT DUE / NOT RECORDED")
        self.assertIn("PDUFA DATE CHANGED", rows[0]["Monitoring alert"])
        self.assertEqual(rows[0]["Conservative PDUFA date"], "2026-10-14")
        self.assertEqual(totals["due"], 1)

    def test_missing_quote_makes_no_marked_profit(self):
        rows, _ = self.check(quote=market(date_str="2026-09-01"))
        self.assertEqual(rows[0]["Trade lifecycle"], "YELLOW — OPEN / QUOTE RECHECK")
        self.assertIsNone(rows[0]["Marked or realized P/L %"])
        self.assertIsNone(rows[0]["Last EOD close USD"])

    def test_future_quote_does_not_pass(self):
        rows, _ = self.check(quote=market(date_str="2026-11-01"))
        self.assertIsNone(rows[0]["Last EOD close USD"])

    def test_unverified_current_pdufa_requires_review(self):
        rows, totals = self.check(program=candidate(verified=False))
        self.assertEqual(rows[0]["Trade lifecycle"], "REVIEW — EXIT DATE UNVERIFIED")
        self.assertEqual(totals["review"], 1)

    def test_missing_entry_date_snapshot_requires_review(self):
        p = trade()
        p["pdufa_date_at_entry"] = ""
        rows, _ = self.check(position=p)
        self.assertEqual(rows[0]["Trade lifecycle"], "REVIEW — EXIT DATE UNVERIFIED")

    def test_exact_trial_mismatch_not_promoted(self):
        p = trade()
        p["nct_id"] = "NCT12345678"
        rows, totals = self.check(position=p)
        self.assertEqual(rows[0]["Trade lifecycle"], "REVIEW — INVALID OR UNMATCHED JOURNAL")
        self.assertEqual(totals["open"], 0)

    def test_duplicate_trade_id_not_trusted(self):
        rows, counts = monitor_positions([trade(), trade()], [candidate()], market(), TODAY)
        self.assertEqual(counts["review"], 2)
        self.assertTrue(all(r["Trade lifecycle"].startswith("REVIEW") for r in rows))

    def test_duplicate_candidate_program_does_not_verify(self):
        rows, _ = monitor_positions([trade()], [candidate(), candidate()], market(), TODAY)
        self.assertTrue(rows[0]["Trade lifecycle"].startswith("REVIEW"))

    def test_future_entry_rejected(self):
        p = trade()
        p["entry_date"] = "2026-10-12"
        rows, _ = self.check(position=p)
        self.assertEqual(rows[0]["Trade lifecycle"], "REVIEW — INVALID OR UNMATCHED JOURNAL")

    def test_partial_exit_rejected(self):
        p = trade()
        p["exit_date"] = "2026-10-10"
        rows, _ = self.check(position=p)
        self.assertEqual(rows[0]["Trade lifecycle"], "REVIEW — INVALID OR UNMATCHED JOURNAL")

    def test_exit_after_cutoff_warns(self):
        p = trade(initial_pdufa=7, closed=True)
        rows, _ = self.check(position=p, program=candidate(pdufa=7),
                             date_value=date(2026, 10, 11))
        self.assertEqual(rows[0]["Trade lifecycle"], "RED — EXIT RECORDED")
        # The recorded close precedes today's due date.
        self.assertNotIn("AFTER scheduled deadline", rows[0]["Monitoring alert"])
