"""Pipeline is the only record genesis for source scans and GEMs."""
import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from pipeline_source_scope import pipeline_origins, source_scope, gem_pipeline_id


def write_rows(path, rows):
    fields = sorted({key for row in rows for key in row})
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


class PipelineOriginPolicyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        write_rows(self.root / "pdufa_candidates.csv", [
            {"event_key": "AAA|DRUG_20261130", "ticker": "AAA", "drug": "Program A"},
        ])
        write_rows(self.root / "phase_pipeline.csv", [
            {"nct_id": "NCT01234567", "ticker": "BBB", "phase": "PHASE3",
             "drug": "Program B"},
        ])
        write_rows(self.root / "company_registry.csv", [
            {"ticker": "AAA", "cik10": "0000000001"},
            {"ticker": "BBB", "cik10": "0000000002"},
            {"ticker": "ORPHAN", "cik10": "0000000003"},
        ])

    def test_pipeline_ingestion_mints_record_id_before_downstream(self):
        ids, tickers = pipeline_origins(self.root, today=date(2026, 10, 15))
        self.assertIn("APPLICATION|AAA|DRUG_20261130", ids)
        self.assertIn("TRIAL|NCT01234567", ids)
        self.assertEqual(tickers["TRIAL|NCT01234567"], "BBB")
        self.assertEqual(tickers["APPLICATION|AAA|DRUG_20261130"], "AAA")
        events, companies = source_scope(self.root, today=date(2026, 10, 15))
        self.assertEqual([row["event_key"] for row in events], ["AAA|DRUG_20261130"])
        self.assertEqual([row["ticker"] for row in companies], ["AAA"])

    def test_gem_cannot_mint_events_from_new_or_mismatched_source(self):
        ids, tickers = pipeline_origins(self.root, today=date(2026, 10, 15))
        application = {"Exact event": "AAA|DRUG_20261130", "Ticker": "AAA"}
        trial = {"Exact event": "", "NCT ID": "NCT01234567", "Ticker": "BBB"}
        self.assertEqual(gem_pipeline_id(application, ids, tickers),
                         "APPLICATION|AAA|DRUG_20261130")
        self.assertEqual(gem_pipeline_id(trial, ids, tickers),
                         "TRIAL|NCT01234567")
        self.assertEqual(gem_pipeline_id({**application, "Ticker": "ORPHAN"}, ids, tickers), "")
        self.assertEqual(gem_pipeline_id({**trial, "Ticker": "AAA"}, ids, tickers), "")
        self.assertEqual(gem_pipeline_id(
            {"Exact event": "ORPHAN|EVENT", "Ticker": "ORPHAN"}, ids, tickers), "")

    def test_sec_verification_scope_rejects_non_pipeline_and_ticker_conflicts(self):
        with patch("pipeline_source_scope.pipeline_origins", return_value=(
            {"APPLICATION|AAA|DRUG_20261130"},
            {"APPLICATION|AAA|DRUG_20261130": "BBB"},
        )):
            events, companies = source_scope(self.root, today=date(2026, 10, 15))
        self.assertEqual(events, [])
        self.assertEqual(companies, [])


if __name__ == "__main__":
    unittest.main()
