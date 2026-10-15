"""FDA exact-event DELTA cache cannot promote amendments, stale targets or unknown decisions."""
import csv
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from scripts import source_verification as v


COMPANY = {"ticker": "ABC", "company": "ABC Pharma", "cik10": "0000000001"}
EVENT = {
    "event_key": "ABC|CANCER", "ticker": "ABC", "company": "ABC Pharma",
    "drug": "Drug A", "indication": "cancer", "nct_id": "NCT00000001",
    "pdufa_date": "2027-03-01",
    "pdufa_evidence_url": "https://www.fda.gov/drugs/approval/abc",
    "outcome": "",
}
SOURCE = "https://www.fda.gov/drugs/approval/abc"


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class FdaDeltaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.data = self.root / "data"
        self.out = self.root / "out"
        self.data.mkdir()
        self.out.mkdir()
        self.event = dict(EVENT)
        write_csv(self.data / "company_registry.csv", [COMPANY])
        self.save_event()

    def tearDown(self):
        self.temporary.cleanup()

    def save_event(self):
        write_csv(self.data / "pdufa_candidates.csv", [self.event])

    def run_scan(self, mode, *, index_hash="a" * 64, index_status="VERIFIED",
                 verified=True):
        seen = []
        def registry(_self, _company):
            return {"verification_status": index_status, "source_sha256": index_hash}
        def regulatory(self, event):
            seen.append(event["event_key"])
            outcome = event.get("outcome", "").upper()
            decision = outcome in {"APPROVED", "CRL"}
            expected_date = event.get("decision_date", "") if decision else event.get("pdufa_date", "")
            row = self.result(event, "FDA", "FDA_DECISION" if decision else "PDUFA_TARGET",
                              "VERIFIED" if verified else "REVIEW_REQUIRED",
                              "Original primary source manually verified", SOURCE,
                              outcome + " " + expected_date if decision else expected_date,
                              expected_date)
            row["source_sha256"] = "b" * 64 if verified else ""
            return [row]
        with patch.object(v.Verifier, "registry", registry), patch.object(v.Verifier, "regulatory", regulatory):
            report = v.verify_source("FDA", self.data, self.out, mode=mode,
                                     as_of=date(2026, 10, 15))
        with (self.out / "fda_verification.csv").open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        return report, rows[0], seen

    def establish_verified_baseline(self):
        result, row, calls = self.run_scan("FULL")
        self.assertEqual(result["fda_claims_live_checked"], 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(row["claim_input_sha256"]), 64)
        self.assertEqual(len(row["monitor_index_sha256"]), 64)
        shutil.copyfile(self.out / "fda_verification.csv",
                        self.data / "pdufa_source_verification.csv")

    def test_unchanged_exact_event_carries_historical_evidence(self):
        self.establish_verified_baseline()
        report, row, seen = self.run_scan("DELTA")
        self.assertEqual(report["fda_claims_carried_forward"], 1)
        self.assertEqual(report["fda_claims_live_checked"], 0)
        self.assertFalse(seen)
        self.assertEqual(row["verification_status"], "VERIFIED")
        self.assertEqual(row["source_sha256"], "b" * 64)
        self.assertIn("CARRIED_FORWARD", row["reason"])

    def test_amended_issuer_filing_reopens_fda_primary(self):
        self.establish_verified_baseline()
        report, _, seen = self.run_scan("DELTA", index_hash="c" * 64)
        self.assertEqual(report["fda_claims_carried_forward"], 0)
        self.assertEqual(len(seen), 1)

    def test_blocked_issuer_index_reopens_fda_primary(self):
        self.establish_verified_baseline()
        report, _, seen = self.run_scan("DELTA", index_status="TECHNICAL_FAILURE", index_hash="")
        self.assertEqual(report["fda_claims_carried_forward"], 0)
        self.assertEqual(len(seen), 1)

    def test_changed_drug_or_trial_or_target_reopens_primary(self):
        for field, value in (("nct_id", "NCT00000002"),
                             ("drug", "Drug B"),
                             ("pdufa_date", "2027-05-01"),
                             ("outcome", "APPROVED")):
            with self.subTest(field=field):
                self.event = dict(EVENT)
                self.save_event()
                self.establish_verified_baseline()
                self.event[field] = value
                if field == "outcome":
                    self.event["decision_date"] = "2026-10-12"
                self.save_event()
                report, _, seen = self.run_scan("DELTA")
                self.assertEqual(report["fda_claims_carried_forward"], 0)
                self.assertEqual(len(seen), 1)

    def test_near_date_and_sunday_full_never_carry(self):
        self.establish_verified_baseline()
        _, _, seen = self.run_scan("FULL")
        self.assertEqual(len(seen), 1)
        self.event["pdufa_date"] = "2026-10-25"
        self.save_event()
        report, _, seen = self.run_scan("DELTA")
        self.assertEqual(report["fda_claims_carried_forward"], 0)
        self.assertEqual(len(seen), 1)

    def test_unverified_claim_is_not_promoted_by_delta(self):
        self.establish_verified_baseline()
        result, _, _ = self.run_scan("DELTA", index_hash="c" * 64, verified=False)
        self.assertEqual(result["findings_verified"], 0)
        shutil.copyfile(self.out / "fda_verification.csv",
                        self.data / "pdufa_source_verification.csv")
        result, row, seen = self.run_scan("DELTA", verified=False)
        self.assertEqual(result["fda_claims_carried_forward"], 0)
        self.assertEqual(row["verification_status"], "REVIEW_REQUIRED")
        self.assertEqual(len(seen), 1)


if __name__ == "__main__":
    unittest.main()
