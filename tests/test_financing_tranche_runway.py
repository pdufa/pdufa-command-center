"""Multiple tranches are cash receipts, NOT multiple separate financing agreements."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from financing_tranche_runway import assess_tranche_runway, load_tranches


def snapshot():
    return {
        "ticker": "ABC", "cik": "0000000001", "as_of": "2026-10-17",
        "cash_includes_restricted": False, "review_flags": [],
        "cash_usd": 100_000_000, "operating_cash_flow_usd": -30_000_000,
        "operating_cash_flow_months": 3,
        "runway_months_cash_only": 10.0,
        "evidence": {
            "companyfacts_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000000001.json",
            "cash": {"form": "10-Q", "accession": "0000000001-26-000001",
                     "period_end": "2026-09-30", "filed": "2026-10-10"},
            "operating_cash_flow": {"form": "10-Q", "accession": "0000000001-26-000001",
                                    "period_end": "2026-09-30", "filed": "2026-10-10"},
        },
    }


def tranche(tranche_id, day, net="10000000", *, agreement="ONE_DEAL",
            status="FUNDED", verification="VERIFIED", restricted="0"):
    return {
        "event_key": "ABC|TRIAL", "ticker": "ABC", "financing_id": agreement,
        "tranche_id": tranche_id, "tranche_status": status,
        "funded_date": day, "expected_date": "",
        "gross_amount_usd": "12000000", "net_cash_received_usd": net,
        "restricted_cash_usd": restricted,
        "source_url": "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex99-1.htm",
        "source_sha256": "a" * 64, "verification_status": verification,
        "notes": "",
    }


class TrancheRunwayTests(unittest.TestCase):
    def assess(self, rows, snap=None):
        return assess_tranche_runway(
            "ABC", snapshot() if snap is None else snap, rows,
            as_of=date(2026, 10, 17), event_key="ABC|TRIAL",
        )

    def test_two_tranches_one_agreement_both_received(self):
        out = self.assess([tranche("T1", "2026-10-02"), tranche("T2", "2026-10-11")])
        self.assertEqual(out["agreement_count"], 1)
        self.assertEqual(out["funded_net_added_usd"], 20_000_000)
        self.assertEqual(sum(bool(x["counted"]) for x in out["tranches"]), 2)
        self.assertEqual(out["status"], "RESEARCH_ESTIMATE")
        self.assertTrue(out["gate_unchanged"])
        self.assertIsNotNone(out["estimated_runway_months"])

    def test_pre_cash_report_tranche_is_not_double_counted(self):
        out = self.assess([tranche("EARLY", "2026-09-23"), tranche("LATE", "2026-10-12")])
        self.assertEqual(out["funded_net_added_usd"], 10_000_000)
        self.assertFalse(out["tranches"][0]["counted"])

    def test_planned_unverified_future_and_restricted_are_excluded(self):
        pending = tranche("PENDING", "", status="CONDITIONAL")
        future = tranche("FUTURE", "2026-11-02")
        gross_only = tranche("GROSS_ONLY", "2026-10-04", net="", verification="DOCUMENTED_GROSS_ONLY")
        restricted = tranche("RESTRICTED", "2026-10-05", restricted="100000")
        valid = tranche("NET", "2026-10-10")
        out = self.assess([pending, future, gross_only, restricted, valid])
        # A partial sum can understate current cash when other already-funded
        # post-report net proceeds remain unknown; withhold precise runway.
        self.assertEqual(out["funded_net_added_usd"], 0)
        self.assertEqual(out["pending_rows"], 1)
        self.assertGreaterEqual(out["unverified_rows"], 3)
        self.assertEqual(out["status"], "RUNWAY_UNVERIFIED")
        self.assertIsNone(out["estimated_runway_months"])

    def test_duplicate_agreement_tranche_stops_projection(self):
        first = tranche("REPEATED", "2026-10-06")
        out = self.assess([first, dict(first)])
        self.assertEqual(out["status"], "RUNWAY_UNVERIFIED")
        self.assertIsNone(out["estimated_runway_months"])

    def test_wrong_issuer_or_missing_hash_cannot_increase_cash(self):
        bad = tranche("BAD", "2026-10-06")
        bad["source_url"] = bad["source_url"].replace("/data/1/", "/data/2/")
        missing = tranche("NO_HASH", "2026-10-07")
        missing["source_sha256"] = ""
        out = self.assess([bad, missing])
        self.assertEqual(out["funded_net_added_usd"], 0)
        self.assertEqual(out["unverified_rows"], 2)

    def test_unverified_cash_baseline_never_gains_pass(self):
        base = snapshot()
        base["review_flags"] = ["SEC SOURCE REVIEW REQUIRED"]
        out = self.assess([tranche("T", "2026-10-11")], base)
        self.assertEqual(out["status"], "RUNWAY_UNVERIFIED")
        self.assertIsNone(out["estimated_runway_months"])

    def test_separate_agreements_recorded_but_not_promoted(self):
        out = self.assess([
            tranche("T1", "2026-10-05", agreement="FIRST"),
            tranche("T1", "2026-10-06", agreement="SECOND"),
        ])
        self.assertEqual(out["agreement_count"], 2)
        self.assertTrue(out["gate_unchanged"])
        self.assertNotIn("entry_authorized", out)

    def test_actual_post_statement_net_unknown_blocks_runway_estimate(self):
        documented_gross = tranche("GROSS", "2026-10-08", net="",
                                   verification="DOCUMENTED_GROSS_ONLY")
        out = self.assess([tranche("NET", "2026-10-11"), documented_gross])
        self.assertEqual(out["agreement_count"], 1)
        self.assertEqual(out["status"], "RUNWAY_UNVERIFIED")
        self.assertIsNone(out["estimated_cash_usd"])
        self.assertIn("unverified net proceeds", out["reason"])

    def test_load_data_folder_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "data" / "financing_tranches.csv"
            file.parent.mkdir()
            sample = tranche("ONE", "2026-10-05")
            with file.open("w", newline="") as stream:
                w = csv.DictWriter(stream, fieldnames=list(sample))
                w.writeheader()
                w.writerow(sample)
            self.assertEqual(len(load_tranches(tmp)["ABC"]), 1)

    def test_load_input_file_accepts_multiple_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "financing_tranches.csv"
            sample = tranche("T1", "2026-10-05")
            with file.open("w", newline="") as stream:
                w = csv.DictWriter(stream, fieldnames=list(sample))
                w.writeheader()
                w.writerow(sample)
            data = load_tranches(tmp)
            self.assertEqual(len(data["ABC"]), 1)


if __name__ == "__main__":
    unittest.main()
