"""Full financing-stage coverage must not regress to cherry-picked close claims."""
from __future__ import annotations

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_financing_batch_review import build_financing_review
from gem_verified_snapshot import source_cleared_gems


def csvwrite(root, name, rows):
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (root / name).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


class FinancingBlockAuditTests(unittest.TestCase):
    def test_clinical_membership_does_not_expand_financing_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csvwrite(root, "pdufa_candidates.csv", [{
                "event_key": "DDD|X", "ticker": "DDD", "drug": "Alpha Drug",
                "phase3_status": "PRIMARY_MET_VERIFIED", "phase3_date": "2026-01-01",
                "nct_id": "NCT00000001",
                "trial_evidence_url": "https://issuer.example/real",
                "pdufa_date": "2027-06-01",
            }])
            active, _, _ = source_cleared_gems(root, as_of=date(2026, 10, 14))
            self.assertEqual(len(active), 1)  # Optional funding keeps GEM research listed.
            rows, summary = build_financing_review(root, as_of=date(2026, 10, 14))
            self.assertEqual(rows, [])
            self.assertEqual(summary["active_benchmark_cleared"], 0)
            self.assertEqual(summary["pending_or_excluded"], 0)

    def test_repository_entire_financing_block_stays_visible(self):
        data = Path(__file__).resolve().parents[1] / "data"
        rows, summary = build_financing_review(data, as_of=date(2026, 10, 14))
        self.assertEqual(len(rows), 38)
        self.assertEqual(summary["financing_programs_reviewed"], 38)
        self.assertGreaterEqual(summary["historically_attested_two_close"], 6)
        self.assertGreaterEqual(summary["active_benchmark_cleared"], 5)
        self.assertEqual(summary["historical_benchmark_cleared"], 1)
        self.assertEqual(summary["trade_entries_authorized"], 0)
        self.assertEqual({r["Ticker"] for r in rows
                          if r["Review status"] == "CLEARED 2/2 — ACTIVE RESEARCH"},
                         {"NTLA", "ZBIO", "PRAX", "MLYS", "SVRA"})
        self.assertEqual({r["Ticker"] for r in rows
                          if r["Review status"] == "CLEARED 2/2 — HISTORICAL / EXIT"},
                         {"SRRK"})
        self.assertEqual(len({r["Exact program"] for r in rows}), 38)
        self.assertEqual(len(rows), sum(summary["by_status"].values()))
        self.assertNotEqual(next(r for r in rows if r["Ticker"] == "COGT"
                                and "NONADVSM" in r["Exact program"])["Review status"],
                            "CLEARED 2/2 — ACTIVE RESEARCH")
        self.assertTrue(all(not row["Trade entry authorized"] for row in rows))
        self.assertGreater(summary["saved_phase3_result_ledger_rows"], 2000)
        self.assertTrue(all(row["Missing evidence / next actions"] for row in rows))

    def test_exact_drug_or_nct_required_for_registry_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csvwrite(root, "pdufa_candidates.csv", [
                {"event_key": "AAA|DRUG_A", "ticker": "AAA", "drug": "Alpha Drug",
                 "indication": "Disease A", "phase3_status": "UNVERIFIED",
                 "nct_id": "", "pdufa_date": "2027-06-01"},
                {"event_key": "AAA|DRUG_B", "ticker": "AAA", "drug": "Beta Drug",
                 "indication": "Disease B", "phase3_status": "UNVERIFIED",
                 "nct_id": "NCT00000002", "pdufa_date": "2027-06-01"},
            ])
            csvwrite(root, "second_financing_status.csv", [
                {"event_key": "AAA|DRUG_A", "second_financing_audit_status":
                 "NO_SECOND_POST_PHASE3_CLOSE_VERIFIED"},
                {"event_key": "AAA|DRUG_B", "second_financing_audit_status":
                 "NO_SECOND_POST_PHASE3_CLOSE_VERIFIED"},
            ])
            csvwrite(root, "phase3_announcements.csv", [
                {"ticker": "AAA", "drug": "Alpha Drug", "nct_id": "NCT00000001",
                 "source_type": "CLINICALTRIALS_RESULTS",
                 "phase3_results_posted_at": "2026-08-01",
                 "phase3_results_source": "https://clinicaltrials.gov/study/NCT00000001"},
                {"ticker": "AAA", "drug": "Unrelated", "nct_id": "NCT00000002",
                 "source_type": "ISSUER_TOPLINE_RELEASE",
                 "phase3_results_posted_at": "2026-08-02",
                 "phase3_results_source": "https://issuer.example/second"},
                {"ticker": "AAA", "drug": "Gamma Drug", "nct_id": "NCT00000003",
                 "source_type": "ISSUER_TOPLINE_RELEASE",
                 "phase3_results_posted_at": "2026-08-02",
                 "phase3_results_source": "https://issuer.example/third"},
            ])
            rows, summary = build_financing_review(root, as_of=date(2026, 10, 14))
            by_key = {row["Exact program"]: row for row in rows}
            self.assertEqual(by_key["AAA|DRUG_A"]["Matched Phase 3 source leads"], 1)
            self.assertIn("NCT00000001", by_key["AAA|DRUG_A"]["Phase 3 discovery examples"])
            self.assertNotIn("NCT00000002",
                             by_key["AAA|DRUG_A"]["Phase 3 discovery examples"])
            self.assertEqual(by_key["AAA|DRUG_B"]["Matched Phase 3 source leads"], 1)
            self.assertIn("NCT00000002", by_key["AAA|DRUG_B"]["Phase 3 discovery examples"])
            self.assertEqual(summary["financing_programs_with_matched_phase3_source_leads"], 2)
            self.assertEqual(summary["active_benchmark_cleared"], 0)
            self.assertTrue(all(not r["Two benchmark clearance"] for r in rows))

    def test_no_invented_financing_for_known_phase3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csvwrite(root, "pdufa_candidates.csv", [
                {"event_key": "DDD|X", "ticker": "DDD", "drug": "Alpha Drug",
                 "phase3_status": "PRIMARY_MET_VERIFIED", "phase3_date": "2026-01-01",
                 "nct_id": "NCT00000001",
                 "trial_evidence_url": "https://issuer.example/real",
                 "pdufa_date": "2027-06-01"},
            ])
            csvwrite(root, "second_financing_status.csv", [
                {"event_key": "DDD|X",
                 "second_financing_audit_status": "NO_SECOND_POST_PHASE3_CLOSE_VERIFIED"},
            ])
            rows, summary = build_financing_review(root, as_of=date(2026, 10, 14))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Review status"],
                             "PRIORITY — P3 VERIFIED; FIND FINANCING")
            self.assertIn("TWO distinct", rows[0]["Missing evidence / next actions"])
            self.assertEqual(summary["active_benchmark_cleared"], 0)

    def test_same_event_duplicate_finance_record_cannot_clear(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csvwrite(root, "pdufa_candidates.csv", [{
                "event_key": "PPP|X", "ticker": "PPP", "drug": "X",
                "phase3_status": "PRIMARY_MET_VERIFIED",
                "phase3_date": "2026-01-02",
                "nct_id": "NCT11111111",
                "trial_evidence_url": "https://issuer.example/readout",
                "pdufa_date": "2027-06-01",
            }])
            f = {"event_key": "PPP|X", "second_financing_status": "CLOSED",
                 "second_financing_closed": "YES",
                 "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
                 "first_financing_date": "2026-02-01",
                 "second_financing_date": "2026-03-01",
                 "first_financing_source":
                 "https://www.sec.gov/Archives/edgar/data/123/a.htm",
                 "second_financing_source":
                 "https://www.sec.gov/Archives/edgar/data/123/b.htm",
                 "verified_as_of": "2026-10-14"}
            csvwrite(root, "second_financing_status.csv", [f, f])
            rows, summary = build_financing_review(root, as_of=date(2026, 10, 14))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["Review status"],
                             "EVENT IDENTITY CONFLICT — MANUAL CHECK")
            self.assertFalse(rows[0]["Two benchmark clearance"])
            self.assertEqual(summary["active_benchmark_cleared"], 0)


if __name__ == "__main__":
    unittest.main()
