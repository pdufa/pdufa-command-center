"""Offline tests for capped, fail-closed GEM SEC financial runway collection."""
import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.collect_gem_runway import eligible_tickers, collect


TODAY = date(2026, 10, 13)
EVENT = "AAA|DRUG_20261201"


def candidate(ticker="AAA", **overrides):
    row = {
        "event_key": ticker + "|DRUG_20261201", "ticker": ticker,
        "phase3_date": "2026-09-01", "phase3_status": "VERIFIED_SUCCESS",
        "pdufa_date": "2026-12-01", "outcome": "",
        "monitor_eligibility": "WATCH",
    }
    row.update(overrides)
    return row


class GemRunwayCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.registry = {"AAA": {"ticker": "AAA", "cik": "0000000123", "company": "Example Biotech", "conflict": False}}

    def write_inputs(self, rows):
        with (self.root / "company_registry.csv").open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=["ticker", "company", "cik10"])
            writer.writeheader()
            writer.writerow({"ticker": "AAA", "company": "Example Biotech", "cik10": "0000000123"})
        with (self.root / "pdufa_candidates.csv").open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=list(candidate()))
            writer.writeheader()
            writer.writerows(rows)

    def test_target_universe_filters_unverified_clinical_and_resolved_events(self):
        rows = [
            candidate(), candidate("BBB", phase3_status="RESULTS_REVIEW"),
            candidate("CCC", outcome="APPROVED"),
            candidate("DDD", pdufa_date="2026-10-15"),
            candidate("EEE", phase3_date="2026-10-20"),
        ]
        self.assertEqual(eligible_tickers(rows, self.registry, as_of=TODAY), ["AAA"])

    def test_dated_source_refresh_publishes_only_successfully_scanned_ticker(self):
        self.write_inputs([candidate()])
        calls = []
        def scanner(ticker, **kwargs):
            calls.append((ticker, kwargs))
            return 1, {"ticker": ticker, "as_of": TODAY.isoformat(),
                       "evidence": {"cash": {"period_end": "2026-09-30"}}}
        report = collect(self.root, as_of=TODAY, agent="Researcher user@example.com", scanner=scanner)
        self.assertEqual(report["target_count"], 1)
        self.assertEqual(report["collected_count"], 1)
        self.assertEqual(report["collector_status"], "COMPLETE")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1]["as_of"], TODAY)
        self.assertEqual(json.loads((self.root/"gem_runway_evidence.json").read_text())["source"],
                         "SEC_STEP4_COMPANYFACTS")

    def test_missing_sec_contact_does_not_promote_saved_old_success(self):
        self.write_inputs([candidate()])
        old = {"ticker": "AAA", "as_of": "2026-10-12", "evidence":
               {"cash": {"period_end": "2026-06-30"}}}
        (self.root/"gem_runway_evidence.json").write_text(json.dumps({
            "schema_version": 1, "source": "SEC_STEP4_COMPANYFACTS",
            "snapshots": [old]}), encoding="utf-8")
        def unexpected(*args, **kwargs):
            raise AssertionError("No SEC requests permitted without identity")
        report = collect(self.root, as_of=TODAY, agent="", scanner=unexpected)
        self.assertEqual(report["collected_count"], 0)
        self.assertEqual(report["collector_status"], "PARTIAL — SOURCE FAILURES")
        self.assertEqual(report["snapshots"], [])
        self.assertEqual(report["history"], [old])

    def test_sec_request_failure_returns_error_without_fake_runway(self):
        self.write_inputs([candidate()])
        def denied(*args, **kwargs):
            raise RuntimeError("SEC HTTP 403")
        report = collect(self.root, as_of=TODAY,
                         agent="Researcher user@example.com", scanner=denied)
        self.assertEqual(report["snapshots"], [])
        self.assertIn("403", report["failures"][0]["reason"])

    def test_no_candidates_does_not_invent_source_coverage(self):
        self.write_inputs([candidate(pdufa_date="2026-10-14")])
        report = collect(self.root, as_of=TODAY, agent="")
        self.assertEqual(report["target_count"], 0)
        self.assertEqual(report["snapshots"], [])


if __name__ == "__main__":
    unittest.main()
