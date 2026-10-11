"""Offline tests for Step 5 all-registered-ticker market scanner; no HTTP."""
import csv
import io
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from market_bulk_scan import (
    RatePacer, csv_output, neutral_score, parse_phase_manifest,
    read_bulk_results, run_bulk, summarize,
)
from market_step5 import evaluate_market

ASOF = date(2026, 10, 10)
EVIDENCE = {"url": "https://clinicaltrials.gov/study/NCT01234567",
            "date": "2026-10-01"}
REG = {
    "AAAA": {"ticker": "AAAA", "company": "A Holdings", "cik": "0000000001",
             "conflict": False},
    "BBBB": {"ticker": "BBBB", "company": "B Bio", "cik": "0000000002",
             "conflict": False},
    "CCCC": {"ticker": "CCCC", "company": "C Pharma", "cik": "0000000003",
             "conflict": False},
    "DDDD": {"ticker": "DDDD", "company": "D Bio", "cik": "0000000004",
             "conflict": False},
    "INVALID": {"ticker": "INVALID", "cik": "", "company": "", "conflict": True},
}


def bars(end=date(2026, 10, 9), size=42):
    days = []
    d = end
    while len(days) < size:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    output = []
    for i, day in enumerate(reversed(days)):
        close = round(10.0 + .04 * i, 3)
        output.append({
            "date": day.isoformat(), "open": close,
            "high": close + .5, "low": close - .5, "close": close,
            "volume": 1000000 + 10000 * i
        })
    return output


class BatchMarketStep5Tests(unittest.TestCase):
    def fake(self, ticker, as_of):
        self.assertIn(ticker, REG)
        self.assertEqual(as_of, ASOF)
        return bars(), {"provider": "TEST EOD", "source_url": "https://example.org/prices"}

    def test_manifest_source_rules_and_fails_closed(self):
        manifest = (
            "ticker,phase,phase_url,phase_date,readout_date\n"
            "BBBB,PRE_RESULTS,https://example.org/study,2026-10-01,\n"
            "CCCC,POST_RESULTS,https://example.org/readout,2026-10-07,2026-10-02\n")
        parsed = parse_phase_manifest(manifest, REG)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed["CCCC"]["phase"], "POST_RESULTS")
        for invalid in (
            "ticker,phase,phase_url,phase_date\nAAAA,BAD,https://example.org,2026-10-01\n",
            "ticker,phase,phase_url,phase_date\nMISSING,PRE_RESULTS,https://example.org,2026-10-01\n",
            "ticker,phase,phase_url,phase_date\nAAAA,PRE_RESULTS,https://example.org,2026-10-01\nAAAA,PRE_RESULTS,https://example.org,2026-10-01\n",
            "ticker,phase\nAAAA,PRE_RESULTS\n",
        ):
            with self.assertRaises(ValueError):
                parse_phase_manifest(invalid, REG)

    def test_scans_all_unique_identities_and_neutral_unknown_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "scans.sqlite3"
            reports = []
            result = run_bulk(ASOF, identities=REG, db_path=db, getter=self.fake,
                              min_interval=.1, on_progress=reports.append)
            self.assertEqual(result["roster"], 4)
            self.assertEqual(result["completed_attempts"], 4)
            self.assertEqual(result["remaining"], 0)
            self.assertEqual(len(result["neutral_ranking"]), 4)
            self.assertEqual(len(result["pre_results_ranking"]), 0)
            self.assertEqual(len(result["post_results_ranking"]), 0)
            self.assertEqual(len(reports), 4)
            self.assertEqual({r["ticker"] for r in result["rows"]},
                             {"AAAA", "BBBB", "CCCC", "DDDD"})
            for row in result["rows"]:
                self.assertIsNotNone(row["neutral_price_volume_score_0_100"])
                self.assertIsNone(row["phase_specific_score_0_100"])
                self.assertEqual(row["phase"], "UNVERIFIED")
                self.assertEqual(row["status"], "REVIEW — PHASE UNVERIFIED")
            self.assertIn("AAAA", csv_output(result["rows"]))
            self.assertEqual(len(read_bulk_results(db)), 4)

    def test_phase_manifest_still_requires_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = {
                "AAAA": {"phase": "PRE_RESULTS", "phase_evidence": EVIDENCE},
                "BBBB": {"phase": "PRE_RESULTS", "phase_evidence": {
                    "url": "http://insecure.example", "date": "2026-10-01"}},
                "CCCC": {"phase": "POST_RESULTS", "phase_evidence": {
                    "url": "https://example.org/readout", "date": "2026-10-07"},
                    "readout_date": "2026-10-02"}
            }
            result = run_bulk(ASOF, identities=REG, phase_manifest=manifest,
                              db_path=Path(folder) / "scans.sqlite",
                              getter=self.fake, min_interval=.1)
            self.assertEqual(len(result["neutral_ranking"]), 4)
            self.assertEqual(len(result["pre_results_ranking"]), 1)
            self.assertEqual(len(result["post_results_ranking"]), 1)
            self.assertEqual({r["ticker"] for r in result["pre_results_ranking"]}, {"AAAA"})
            self.assertEqual({r["ticker"] for r in result["post_results_ranking"]}, {"CCCC"})
            pending = next(r for r in result["rows"] if r["ticker"] == "BBBB")
            self.assertEqual(pending["phase_specific_score_0_100"], None)

    def test_resume_skips_success_retries_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "scans.sqlite"
            calls = []
            fail_b = {"value": True}

            def getter(ticker, as_of):
                calls.append(ticker)
                if ticker == "BBBB" and fail_b["value"]:
                    raise RuntimeError("HTTP 429 — throttled")
                return self.fake(ticker, as_of)

            partial = run_bulk(ASOF, identities=REG, db_path=db, getter=getter,
                               max_new=2, min_interval=.1)
            self.assertEqual(partial["completed_attempts"], 2)
            self.assertEqual(partial["remaining"], 2)
            self.assertEqual(partial["status_counts"]["FAILED"], 1)
            self.assertEqual(len(calls), 2)

            fail_b["value"] = False
            finished = run_bulk(ASOF, identities=REG, db_path=db, getter=getter,
                                min_interval=.1)
            self.assertEqual(finished["completed_attempts"], 4)
            self.assertEqual(finished["remaining"], 0)
            self.assertEqual(len(finished["neutral_ranking"]), 4)
            self.assertEqual(calls.count("AAAA"), 1)
            self.assertEqual(calls.count("BBBB"), 2)
            self.assertEqual(len(read_bulk_results(db, finished["run_key"])), 4)
            again = run_bulk(ASOF, identities=REG, db_path=db, getter=getter,
                             min_interval=.1)
            self.assertEqual(again["run_key"], finished["run_key"])
            self.assertEqual(len(calls), 5)

    def test_completed_failed_are_not_false_success(self):
        with tempfile.TemporaryDirectory() as folder:
            def blocked(ticker, as_of):
                raise RuntimeError("No provider data")
            result = run_bulk(ASOF, identities=REG, db_path=Path(folder) / "db.sqlite",
                              getter=blocked, min_interval=.1)
            self.assertEqual(result["status_counts"]["FAILED"], 4)
            self.assertEqual(result["completed_attempts"], 4)
            self.assertEqual(len(result["neutral_ranking"]), 0)
            self.assertEqual(result["remaining"], 0)
            self.assertTrue(all(row["error"] for row in result["rows"]))

    def test_score_withholds_invalid_or_insufficient_price_data(self):
        with tempfile.TemporaryDirectory() as folder:
            def incomplete(ticker, as_of):
                return bars(size=20), {"provider": "TEST EOD"}
            result = run_bulk(ASOF, identities=REG, db_path=Path(folder) / "db.sqlite",
                              getter=incomplete, min_interval=.1)
            self.assertEqual(len(result["neutral_ranking"]), 0)
            self.assertEqual(result["status_counts"]["REVIEW — INCOMPLETE PRICE DATA"], 4)

    def test_latest_bulk_run_restricts_universe_and_no_false_cross_run_leak(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder) / "scans.sqlite"
            first = run_bulk(ASOF, identities=REG, db_path=db, getter=self.fake, min_interval=.1)
            subset = {key: REG[key] for key in ("AAAA", "CCCC")}
            second = run_bulk(ASOF, identities=subset, db_path=db, getter=self.fake,
                              min_interval=.1)
            self.assertNotEqual(first["run_key"], second["run_key"])
            self.assertEqual(len(read_bulk_results(db, first["run_key"])), 4)
            self.assertEqual(len(read_bulk_results(db, second["run_key"])), 2)
            self.assertEqual(summarize(read_bulk_results(db, second["run_key"]))["completed_attempts"], 2)

    def test_invalid_future_date_and_workers_cannot_start(self):
        with tempfile.TemporaryDirectory() as folder:
            for invalid in ("2099-01-01", "bad-date"):
                with self.assertRaises(ValueError):
                    run_bulk(invalid, identities=REG, db_path=Path(folder) / "x.sqlite",
                             getter=self.fake, min_interval=.1)
            for workers in (0, 5):
                with self.assertRaises(ValueError):
                    run_bulk(ASOF, identities=REG, db_path=Path(folder) / "x.sqlite",
                             getter=self.fake, max_workers=workers, min_interval=.1)
            with self.assertRaises(ValueError):
                RatePacer(0)
            with self.assertRaises(ValueError):
                run_bulk(ASOF, identities={}, db_path=Path(folder) / "x.sqlite",
                         getter=self.fake, min_interval=.1)


if __name__ == "__main__":
    unittest.main()
