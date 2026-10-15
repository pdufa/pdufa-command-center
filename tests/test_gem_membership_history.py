"""Per-exact-Pipeline-ID GEM JR/GEM stage history, PDUFA expiry and promotions."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_membership_history import (
    empty_history, update_history, membership_fields, departed_stage_rows,
    read_history, write_history,
)
from scripts.update_gem_membership import stage_exit_reasons


def trial(pid, ticker="ABC", drug="Test", pdufa="2026-10-17"):
    return {
        "Pipeline ID": pid, "Ticker": ticker, "Drug": drug,
        "Exact program": pid, "NCT ID": pid.removeprefix("TRIAL|"),
        "PDUFA date (saved)": pdufa,
    }


class GemMembershipHistoryTests(unittest.TestCase):
    def test_independent_first_found_dates_and_promotion_reason(self):
        pid = "TRIAL|NCT11111111"
        old = update_history(
            empty_history(), {"GEM_JR": [trial(pid)], "GEM": []},
            observed_on="2026-10-10")
        promoted = update_history(
            old, {"GEM_JR": [], "GEM": [trial(pid)]},
            observed_on="2026-10-15",
            exit_reasons={"GEM_JR": {pid: "PROMOTED_TO_GEM"}, "GEM": {}})
        self.assertEqual(membership_fields(promoted, "GEM_JR", pid)["Date Found"],
                         "2026-10-10")
        self.assertEqual(membership_fields(promoted, "GEM_JR", pid)["Date Left"],
                         "2026-10-15")
        self.assertEqual(membership_fields(promoted, "GEM", pid)["Date Found"],
                         "2026-10-15")
        self.assertEqual(departed_stage_rows(promoted, "GEM_JR")[0]["Leave Reason"],
                         "PROMOTED_TO_GEM")
        self.assertEqual(departed_stage_rows(promoted, "GEM"), [])
        archive = departed_stage_rows(promoted, "GEM_JR")[0]
        self.assertEqual(archive["Days in List"], 5)
        self.assertEqual(archive["Current Location"], "GEM ACTIVE")

    def test_pdufa_three_days_before_is_not_expired(self):
        pid = "APPLICATION|ABC|ONE"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (root / "pdufa_candidates.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=[
                    "event_key", "pdufa_date", "ticker", "outcome"])
                w.writeheader()
                w.writerow({"event_key": "ABC|ONE", "ticker": "ABC",
                            "pdufa_date": "2026-10-17", "outcome": ""})
            before = update_history(
                empty_history(),
                {"GEM_JR": [trial(pid)], "GEM": []},
                observed_on="2026-10-13")
            # At PDUFA -3, the eligible stage snapshot must remain active.
            active = {"GEM_JR": [trial(pid)], "GEM": []}
            warnings = stage_exit_reasons(root, before, active,
                                          as_of=date(2026, 10, 14))
            self.assertEqual(warnings["GEM_JR"], {})
            tracked = update_history(before, active, observed_on="2026-10-14",
                                     exit_reasons=warnings)
            self.assertEqual(tracked["stages"]["GEM_JR"]["entries"][pid]["status"],
                             "ACTIVE")
            # The first complete scan AFTER the PDUFA date archives the program.
            empty = {"GEM_JR": [], "GEM": []}
            expired_reasons = stage_exit_reasons(
                root, tracked, empty, as_of=date(2026, 10, 18))
            self.assertEqual(expired_reasons["GEM_JR"][pid], "PDUFA_EXPIRED")
            departed = update_history(tracked, empty, observed_on="2026-10-18",
                                      exit_reasons=expired_reasons)
            row = departed_stage_rows(departed, "GEM_JR")[0]
            self.assertEqual(row["Date Found"], "2026-10-13")
            self.assertEqual(row["Date Left"], "2026-10-18")
            self.assertEqual(row["PDUFA Date"], "2026-10-17")
            self.assertEqual(row["Leave Reason"], "PDUFA_EXPIRED")
            self.assertEqual(row["Days in List"], 5)
            self.assertEqual(row["Current Location"], "EXPIRED / PREVIOUS")

    def test_two_trials_same_ticker_do_not_share_membership(self):
        first, second = "TRIAL|NCT00000001", "TRIAL|NCT00000002"
        old = update_history(empty_history(), {
            "GEM_JR": [trial(first), trial(second)], "GEM": []},
            observed_on="2026-10-12")
        new = update_history(old, {
            "GEM_JR": [trial(second)], "GEM": [trial(first)]},
            observed_on="2026-10-15",
            exit_reasons={"GEM_JR": {first: "PROMOTED_TO_GEM"}})
        self.assertEqual(new["stages"]["GEM_JR"]["entries"][second]["status"], "ACTIVE")
        self.assertEqual(new["stages"]["GEM_JR"]["entries"][first]["status"], "LEFT")
        self.assertEqual(membership_fields(new, "GEM", first)["Date Found"], "2026-10-15")
        self.assertEqual(len(departed_stage_rows(new, "GEM_JR")), 1)

    def test_reentry_keeps_earliest_found_and_periods(self):
        pid = "TRIAL|NCT22222222"
        old = update_history(empty_history(), {
            "GEM_JR": [trial(pid)], "GEM": []}, observed_on="2026-10-01")
        left = update_history(old, {"GEM_JR": [], "GEM": []},
                              observed_on="2026-10-05")
        again = update_history(left, {"GEM_JR": [trial(pid)], "GEM": []},
                               observed_on="2026-10-12")
        fields = membership_fields(again, "GEM_JR", pid)
        self.assertEqual(fields["Date Found"], "2026-10-01")
        self.assertEqual(fields["Date Re-entered"], "2026-10-12")
        self.assertEqual(fields["Date Left"], "")
        self.assertEqual(len(departed_stage_rows(again, "GEM_JR")), 1)
        self.assertEqual(departed_stage_rows(again, "GEM_JR")[0]["Date Left"],
                         "2026-10-05")

    def test_missing_stage_snapshot_and_backdate_refused(self):
        with self.assertRaises(ValueError):
            update_history(empty_history(), {"GEM_JR": []},
                           observed_on="2026-10-13")
        prior = update_history(empty_history(), {"GEM_JR": [], "GEM": []},
                               observed_on="2026-10-15")
        with self.assertRaises(ValueError):
            update_history(prior, {"GEM_JR": [], "GEM": []},
                           observed_on="2026-10-14")

    def test_history_is_durable_and_does_not_invent_dates(self):
        pid = "TRIAL|NCT12345678"
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                membership_fields(read_history(tmp), "GEM", pid)["Date Found"],
                "NOT YET TRACKED")
            tracked = update_history(empty_history(), {
                "GEM_JR": [], "GEM": [trial(pid, ticker="XYZ")]},
                observed_on="2026-10-15")
            self.assertTrue(write_history(tmp, tracked))
            self.assertFalse(write_history(tmp, tracked))
            self.assertEqual(
                membership_fields(read_history(tmp), "GEM", pid)["Date Found"],
                "2026-10-15")


if __name__ == "__main__":
    unittest.main()
