"""Regression: real program evidence clears two GEM benchmarks, never trade gates."""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_verified_snapshot import source_cleared_gems


def write(root, name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (root / name).open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=fields)
        output.writeheader()
        output.writerows(rows)


class ExactGEMClearanceTests(unittest.TestCase):
    def test_repository_has_two_current_programs_and_historical_srrk(self):
        root = Path(__file__).resolve().parents[1] / "data"
        active, historical, sec_current = source_cleared_gems(
            root, as_of=date(2026, 10, 14))
        self.assertIn("NTLA", {r["Ticker"] for r in active})
        self.assertIn("ZBIO", {r["Ticker"] for r in active})
        self.assertIn("SRRK", {r["Ticker"] for r in historical})
        self.assertNotIn("SRRK", {r["Ticker"] for r in active})
        self.assertFalse(sec_current)
        for row in active:
            self.assertEqual(row["Two-benchmark status"],
                             "PASS — BOTH BENCHMARKS SOURCE-CLEARED")
            self.assertIn("ENTRY GATES ON HOLD", row["Trade status"])
            self.assertTrue(row["Phase 3 source"].startswith("https://"))
            self.assertTrue(row["First SEC source"].startswith("https://www.sec.gov/"))
            self.assertTrue(row["Second SEC source"].startswith("https://www.sec.gov/"))
        self.assertEqual(
            next(r for r in active if r["Ticker"] == "NTLA")["NCT ID"],
            "NCT06634420")
        self.assertEqual(
            next(r for r in active if r["Ticker"] == "ZBIO")["NCT ID"],
            "NCT05662241")

    def test_no_cross_program_financing_borrow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "pdufa_candidates.csv", [
                {"event_key": "TEST|A", "ticker": "TEST", "drug": "A",
                 "nct_id": "NCT11111111", "phase3_status": "PRIMARY_MET_VERIFIED",
                 "phase3_date": "2026-01-02", "trial_evidence_url": "https://issuer.example/readout",
                 "pdufa_date": "2027-06-01"},
                {"event_key": "TEST|B", "ticker": "TEST", "drug": "B",
                 "nct_id": "NCT22222222", "phase3_status": "UNVERIFIED",
                 "phase3_date": "", "trial_evidence_url": "", "pdufa_date": "2027-06-01"},
            ])
            write(root, "second_financing_status.csv", [{
                "event_key": "TEST|B", "second_financing_status": "CLOSED",
                "second_financing_closed": "YES",
                "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                "first_financing_date": "2026-02-01",
                "second_financing_date": "2026-03-01",
                "first_financing_source": "https://www.sec.gov/Archives/a",
                "second_financing_source": "https://www.sec.gov/Archives/b",
                "verified_as_of": "2026-10-14",
            }])
            active, historical, sec = source_cleared_gems(root, as_of=date(2026, 10, 14))
            self.assertEqual(active, [])
            self.assertEqual(historical, [])
            self.assertFalse(sec)

    def test_expired_or_resolved_program_never_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "pdufa_candidates.csv", [
                {"event_key": "TST|READY", "ticker": "TST", "drug": "X",
                 "nct_id": "NCT11111111", "phase3_status": "PRIMARY_MET_VERIFIED",
                 "phase3_date": "2026-01-02",
                 "trial_evidence_url": "https://issuer.example/readout",
                 "pdufa_date": "2026-10-16", "outcome": ""},
            ])
            write(root, "second_financing_status.csv", [{
                "event_key": "TST|READY", "second_financing_status": "CLOSED",
                "second_financing_closed": "YES",
                "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                "first_financing_date": "2026-02-01",
                "second_financing_date": "2026-03-01",
                "first_financing_source": "https://www.sec.gov/Archives/a",
                "second_financing_source": "https://www.sec.gov/Archives/b",
                "verified_as_of": "2026-10-14",
            }])
            active, historical, _ = source_cleared_gems(root, as_of=date(2026, 10, 14))
            self.assertEqual(active, [])
            self.assertEqual(len(historical), 1)
            self.assertEqual(historical[0]["Trade status"], "HISTORICAL / NO NEW ENTRY")

    def test_overview_presents_clearances_while_separating_candidates(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root / "gem_potential_ui.py").read_text(encoding="utf-8")
        self.assertIn("### GEM — TWO BENCHMARKS VERIFIED", ui)
        self.assertIn("source_cleared_gems(root)", ui)
        self.assertIn("GLOBAL SEC SOURCE CHECK PARTIAL/STALE", ui)
        self.assertIn("### POTENTIAL GEMs — PENDING RESEARCH", ui)


if __name__ == "__main__":
    unittest.main()
