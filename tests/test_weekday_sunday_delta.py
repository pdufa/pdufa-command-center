"""Sunday complete / weekday changed-only evidence regression tests."""
import csv
import hashlib
import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from scripts.nightly_start import decision
from scripts import source_verification as verify


def stamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class SundayScheduleTests(unittest.TestCase):
    def test_sunday_pacific_full_even_after_midnight_recovery(self):
        for at, cron in (
            ("2026-10-19T03:00:00Z", "0 3 * * *"),
            ("2026-10-19T08:05:00Z", "5 8 * * *"),
            ("2026-11-09T04:00:00Z", "0 4 * * *"),
        ):
            with self.subTest(at=at):
                r = decision("schedule", cron, [], now=stamp(at))
                self.assertTrue(r["run"])
                self.assertEqual(r["scan_mode"], "FULL")
                self.assertEqual(r["gem_action"], "RESCAN_ALL")

    def test_other_nights_are_delta(self):
        r = decision("schedule", "0 3 * * *", [],
                     now=stamp("2026-10-20T03:00:00Z"))
        self.assertTrue(r["run"])
        self.assertEqual(r["scan_mode"], "DELTA")
        self.assertEqual(r["gem_action"], "REVERIFY_PARTIAL")

    def test_manual_full_sunday_but_monday_manual_is_delta(self):
        sun = decision("workflow_dispatch", "", [],
                       now=stamp("2026-10-18T18:00:00Z"))
        mon = decision("workflow_dispatch", "", [],
                       now=stamp("2026-10-19T18:00:00Z"))
        self.assertEqual(sun["scan_mode"], "FULL")
        self.assertEqual(mon["scan_mode"], "DELTA")


class SecCarryForwardTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.out = self.root / "reports"
        self.out.mkdir()
        self.cik = "0000000001"
        self.event_key = "ABC|DRUG"
        self.sec_url = "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/ex99-1.htm"
        self.payload = {"cik": 1, "tickers": ["ABC"], "filings": {"recent": {
            "form": ["8-K"], "filingDate": ["2026-10-10"],
            "accessionNumber": ["0000000001-26-000001"],
            "primaryDocument": ["report.htm"],
        }}}
        self.events = [{"event_key": self.event_key, "ticker": "ABC",
                        "company": "ABC Pharma", "financing_close_date": "2026-10-01",
                        "financing_evidence_url": self.sec_url}]
        companies = [{"ticker": "ABC", "company": "ABC Pharma", "cik10": self.cik}]
        self.write("pdufa_candidates.csv", self.events)
        self.write("company_registry.csv", companies)
        self.seed()

    def tearDown(self):
        self.t.cleanup()

    def write(self, name, rows):
        with (self.data / name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def seed(self):
        raw = json.dumps(self.payload).encode()
        inventory = {"event_key": "REGISTRY:ABC", "ticker": "ABC",
                     "category": "SEC", "claim": "FILINGS_INVENTORY",
                     "verification_status": "VERIFIED", "source_sha256": hashlib.sha256(raw).hexdigest()}
        finance = {"event_key": self.event_key, "ticker": "ABC",
                   "category": "SEC", "claim": "FINANCING_CLOSURE",
                   "verification_status": "VERIFIED", "verification_required": "YES",
                   "source_url": self.sec_url, "expected": "2026-10-01",
                   "source_sha256": "a" * 64,
                   "checked_at": "2026-10-14T12:00:00+00:00",
                   "evidence": "Previously verified SEC funded closing"}
        for row in (inventory, finance):
            row.setdefault("verification_required", "YES")
        with (self.data / "pdufa_source_verification.csv").open(
            "w", newline="", encoding="utf-8"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=verify.FIELDS)
            writer.writeheader()
            writer.writerows([inventory, finance])

    def fake(self, calls):
        def fetch(url):
            calls.append(url)
            if "data.sec.gov/submissions/" in url:
                return json.dumps(self.payload).encode()
            if url == self.sec_url:
                return (b"On October 1, 2026 the Company completed a public offering "
                        b"and received $10 million in gross proceeds.")
            raise AssertionError("Unexpected URL: " + url)
        return fetch

    def test_unchanged_index_preserves_primary_proof_without_refetch(self):
        calls = []
        report = verify.verify_source("SEC", self.data, self.out,
            fetch=self.fake(calls), as_of=date(2026, 10, 15), mode="DELTA")
        self.assertEqual(report["sec_closures_carried_forward"], 1)
        self.assertEqual(report["sec_financing_closures_live_checked"], 0)
        self.assertNotIn(self.sec_url, calls)
        with (self.out / "sec_verification.csv").open(newline="") as f:
            rows = list(csv.DictReader(f))
        closing = next(x for x in rows if x["claim"] == "FINANCING_CLOSURE")
        self.assertEqual(closing["verification_status"], "VERIFIED")
        self.assertEqual(closing["source_sha256"], "a" * 64)
        self.assertIn("CARRIED_FORWARD", closing["reason"])

    def test_new_amendment_reopens_primary_document(self):
        self.payload["filings"]["recent"]["form"].insert(0, "8-K/A")
        self.payload["filings"]["recent"]["filingDate"].insert(0, "2026-10-15")
        self.payload["filings"]["recent"]["accessionNumber"].insert(0, "0000000001-26-000002")
        self.payload["filings"]["recent"]["primaryDocument"].insert(0, "amended.htm")
        calls = []
        report = verify.verify_source("SEC", self.data, self.out,
            fetch=self.fake(calls), as_of=date(2026, 10, 15), mode="DELTA")
        self.assertEqual(report["sec_closures_carried_forward"], 0)
        self.assertEqual(report["sec_financing_closures_live_checked"], 1)
        self.assertIn(self.sec_url, calls)

    def test_full_forces_primary_document_recheck(self):
        calls = []
        report = verify.verify_source("SEC", self.data, self.out,
            fetch=self.fake(calls), as_of=date(2026, 10, 15), mode="FULL")
        self.assertEqual(report["sec_closures_carried_forward"], 0)
        self.assertIn(self.sec_url, calls)


if __name__ == "__main__":
    unittest.main()
