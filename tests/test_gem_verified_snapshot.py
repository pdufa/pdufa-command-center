"""Regression: verified successful Phase 3 qualifies GEM without second-finance gate."""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from gem_verified_snapshot import source_cleared_gems


def write(root, name, rows):
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (root / name).open("w", encoding="utf-8", newline="") as stream:
        output = csv.DictWriter(stream, fieldnames=fields)
        output.writeheader()
        output.writerows(rows)


class ExactGEMClearanceTests(unittest.TestCase):
    def test_repository_phase3_gems_include_unfinanced_gist_program(self):
        root = Path(__file__).resolve().parents[1] / "data"
        active, historical, sec_current = source_cleared_gems(
            root, as_of=date(2026, 10, 14))
        self.assertIn("NTLA", {r["Ticker"] for r in active})
        self.assertIn("ZBIO", {r["Ticker"] for r in active})
        self.assertIn("PRAX", {r["Ticker"] for r in active})
        self.assertIn("MLYS", {r["Ticker"] for r in active})
        self.assertIn("SVRA", {r["Ticker"] for r in active})
        self.assertEqual({r["Ticker"] for r in active}, {"NTLA", "ZBIO", "PRAX", "MLYS", "SVRA", "COGT"})
        self.assertIn("SRRK", {r["Ticker"] for r in historical})
        self.assertNotIn("SRRK", {r["Ticker"] for r in active})
        self.assertFalse(next(r for r in active if r["Ticker"] == "COGT")["Second financing verified"])
        self.assertIn("OPTIONAL", next(r for r in active if r["Ticker"] == "COGT")["Two-benchmark status"])
        self.assertFalse(sec_current)
        by_ticker = {r["Ticker"]: r for r in active}
        self.assertEqual(by_ticker["SVRA"]["PDUFA days left"], 39)
        self.assertEqual(by_ticker["MLYS"]["PDUFA days left"], 69)
        self.assertEqual(by_ticker["PRAX"]["PDUFA days left"], 107)
        self.assertEqual(by_ticker["NTLA"]["PDUFA days left"], 147)
        self.assertEqual(by_ticker["ZBIO"]["PDUFA days left"], 225)
        self.assertEqual(by_ticker["SVRA"]["PDUFA timing window"], "31–90 DAYS — PRIMARY MONITOR")
        self.assertEqual(by_ticker["NTLA"]["PDUFA timing window"], ">90 DAYS — EARLY MONITOR")
        self.assertTrue(by_ticker["NTLA"]["PDUFA verified"])
        self.assertFalse(by_ticker["ZBIO"]["PDUFA verified"])
        for row in active:
            self.assertTrue(row["Two-benchmark status"].startswith("PASS — SUCCESSFUL PHASE 3"))
            self.assertIn("ENTRY GATES ON HOLD", row["Trade status"])
            self.assertTrue(row["Phase 3 source"].startswith("https://"))
            if row["Second financing verified"]:
                self.assertTrue(row["First SEC source"].startswith("https://www.sec.gov/"))
                self.assertTrue(row["Second SEC source"].startswith("https://www.sec.gov/"))
        self.assertEqual(
            next(r for r in active if r["Ticker"] == "NTLA")["NCT ID"],
            "NCT06634420")
        self.assertEqual(
            next(r for r in active if r["Ticker"] == "ZBIO")["NCT ID"],
            "NCT05662241")

    def test_pre_oct15_gem_clearance_without_pipeline_preserves_exact_phase3(self):
        root = Path(__file__).resolve().parents[1] / "data"
        with patch("gem_verified_snapshot.pipeline_origins", return_value=(set(), {})):
            active, historical, _ = source_cleared_gems(
                root, as_of=date(2026, 10, 14))
        self.assertEqual({r["Ticker"] for r in active},
                         {"NTLA", "ZBIO", "PRAX", "MLYS", "SVRA", "COGT"})
        self.assertIn("SRRK", {r["Ticker"] for r in historical})
        self.assertTrue(all(r["Two-benchmark status"].startswith("PASS — SUCCESSFUL PHASE 3") for r in active))
        self.assertTrue(all(r["Pipeline linkage"] ==
                            "SOURCE-CLEARED — PIPELINE INTAKE PENDING" for r in active))
        self.assertTrue(all("ON HOLD" in r["Trade status"] for r in active))

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
                "first_financing_source": "https://www.sec.gov/Archives/edgar/data/123/first.htm",
                "second_financing_source": "https://www.sec.gov/Archives/edgar/data/123/second.htm",
                "verified_as_of": "2026-10-14",
            }])
            active, historical, sec = source_cleared_gems(root, as_of=date(2026, 10, 14))
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["Ticker"], "TEST")
            self.assertEqual(active[0]["NCT ID"], "NCT11111111")
            self.assertFalse(active[0]["Second financing verified"])
            self.assertEqual(historical, [])
            self.assertFalse(sec)

    def test_missing_financing_file_never_suppresses_successful_phase3(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write(root, "pdufa_candidates.csv", [{
                "event_key": "SOLO|PROGRAM", "ticker": "SOLO", "drug": "Medicine",
                "nct_id": "NCT12345678", "phase3_status": "PRIMARY_MET_VERIFIED",
                "phase3_date": "2026-09-04",
                "trial_evidence_url": "https://issuer.example/verified-phase3",
                "pdufa_date": "2027-05-20", "new_dilution_flag": "UNKNOWN",
            }])
            active, previous, _ = source_cleared_gems(root, as_of=date(2026, 10, 18))
            self.assertEqual(len(active), 1)
            self.assertEqual(previous, [])
            self.assertEqual(active[0]["Pipeline ID"], "APPLICATION|SOLO|PROGRAM")
            self.assertEqual(active[0]["Second financing requirement"], "OPTIONAL")
            self.assertFalse(active[0]["Second financing verified"])
            self.assertIn("Dilution exposure not independently cleared", active[0]["Still needed"])
            self.assertIn("ENTRY GATES ON HOLD", active[0]["Trade status"])

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
                "first_financing_source": "https://www.sec.gov/Archives/edgar/data/123/first.htm",
                "second_financing_source": "https://www.sec.gov/Archives/edgar/data/123/second.htm",
                "verified_as_of": "2026-10-14",
            }])
            active, historical, _ = source_cleared_gems(root, as_of=date(2026, 10, 14))
            self.assertEqual(len(active), 1)
            self.assertEqual(historical, [])
            self.assertIn("NO NEW ENTRY — PDUFA −3", active[0]["Trade status"])
            # The program is tracked as research even on PDUFA day itself.
            event_day, event_history, _ = source_cleared_gems(
                root, as_of=date(2026, 10, 16))
            self.assertEqual(len(event_day), 1)
            self.assertEqual(event_history, [])
            expired, archived, _ = source_cleared_gems(
                root, as_of=date(2026, 10, 17))
            self.assertEqual(expired, [])
            self.assertEqual(len(archived), 1)
            self.assertEqual(archived[0]["Trade status"], "HISTORICAL / NO NEW ENTRY")

    def test_overview_presents_clearances_while_separating_candidates(self):
        root = Path(__file__).resolve().parents[1]
        ui = (root / "gem_potential_ui.py").read_text(encoding="utf-8")
        self.assertIn("### GEM — TWO BENCHMARKS VERIFIED", ui)
        self.assertIn("source_cleared_gems(root)", ui)
        self.assertIn("GLOBAL SEC SOURCE CHECK PARTIAL/STALE", ui)
        self.assertIn("### POTENTIAL GEMs — PENDING RESEARCH", ui)


if __name__ == "__main__":
    unittest.main()
