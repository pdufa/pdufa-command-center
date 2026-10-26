import copy
import csv
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from listing_exclusions import validated_listing_exclusions, resolved_pipeline_status
from scripts.phase_pipeline import universe_gate, scan, read_rows, COLUMNS

NOW = datetime(2026, 10, 11, 6, tzinfo=timezone.utc)
RECORD = {"ticker": "TBPH", "company": "Theravance Biopharma, Inc.",
          "cik10": "0001583107", "status": "SUSPENDED — MERGER CLOSED",
          "effective_date": "2026-09-24", "source_date": "2026-09-23",
          "source_url": "https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-668",
          "checked_at": "2026-10-11T05:00:00+00:00"}
REGISTRY = [{k: RECORD[k] for k in ("ticker", "company", "cik10")}]


class ListingExclusionTests(unittest.TestCase):
    def test_exchange_notice_matches_exact_issuer(self):
        result = validated_listing_exclusions({"records": [RECORD]}, REGISTRY, NOW)
        self.assertEqual(result, {"TBPH": RECORD})
        self.assertEqual(universe_gate({"market_cap_status": "NOT_LISTED"}, NOW.date())[0], "FAIL")

    def test_reused_ticker_wrong_issuer_and_duplicate_notices_fail_closed(self):
        for field, value in (("cik10", "0000000001"), ("company", "Other issuer"), ("ticker", "OTHER")):
            record = {**RECORD, field: value}
            self.assertFalse(validated_listing_exclusions({"records": [record]}, REGISTRY, NOW))
        self.assertFalse(validated_listing_exclusions({"records": [RECORD, RECORD]}, REGISTRY, NOW))
        self.assertFalse(validated_listing_exclusions({"records": [RECORD]}, REGISTRY * 2, NOW))

    def test_unclosed_future_undated_or_unapproved_sources_are_rejected(self):
        for patch in ({"status": "MERGER ANNOUNCED"}, {"effective_date": "2026-11-01"},
                      {"checked_at": "2026-10-12T00:00:00+00:00"}, {"checked_at": "2026-10-11"},
                      {"source_date": ""}, {"source_date": "2026-09-25"},
                      {"source_url": "https://www.nasdaqtrader.com.evil.test/TraderNews.aspx?id=ECA2026-668"}):
            self.assertFalse(validated_listing_exclusions({"records": [{**RECORD, **patch}]}, REGISTRY, NOW), patch)

    def test_only_the_accounted_for_quote_warning_is_resolved(self):
        state = {"status": "COMPLETE WITH WARNINGS", "complete": True, "errors": [],
                 "market_cap_source_unavailable": 1, "finished_at": "2026-10-10T17:29:18Z"}
        caps = [{"ticker": "TBPH", "market_cap_status": "REVIEW"},
                {"ticker": "ABC", "market_cap_status": "VERIFIED"}]
        before = copy.deepcopy(state)
        self.assertEqual(resolved_pipeline_status(state, caps, {"TBPH": RECORD}), ("COMPLETE", 1))
        self.assertEqual(state, before)
        for patch in ({"complete": False}, {"errors": ["registry timeout"]},
                      {"market_cap_source_unavailable": 2}, {"status": "PARTIAL"}):
            changed = {**state, **patch}
            self.assertEqual(resolved_pipeline_status(changed, caps, {"TBPH": RECORD}), (changed["status"], 0))
        self.assertEqual(resolved_pipeline_status(state, caps, {}), (state["status"], 0))
        other_missing = caps + [{"ticker": "XYZ", "market_cap_status": "REVIEW"}]
        self.assertEqual(resolved_pipeline_status({**state, "market_cap_source_unavailable": 2}, other_missing,
                                                 {"TBPH": RECORD}), (state["status"], 0))


    def test_published_qncx_to_irla_notice_retains_historical_programs_only(self):
        ledger = json.loads((Path(__file__).resolve().parents[1]
                             / "data/phase_pipeline_listing_exclusions.json").read_text())
        now = datetime(2026, 10, 26, 14, tzinfo=timezone.utc)
        registry = [*REGISTRY, {
            "ticker": "QNCX", "company": "Quince Therapeutics, Inc.",
            "cik10": "0001662774",
        }]
        result = validated_listing_exclusions(ledger, registry, now)
        self.assertEqual(set(result), {"TBPH", "QNCX"})
        changed = result["QNCX"]
        self.assertEqual(changed["replacement_ticker"], "IRLA")
        self.assertEqual(changed["status"], "SYMBOL CHANGED — OLD TICKER RETIRED")
        self.assertEqual(changed["effective_date"], "2026-10-12")
        self.assertEqual(changed["source_url"],
                         "https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-724")
        self.assertNotIn("IRLA", result,
                         "Successor IRLA is not automatically a verified candidate")
        self.assertEqual(universe_gate({"ticker": "QNCX",
                         "market_cap_status": "NOT_LISTED"}, now.date())[0], "FAIL")

    def test_predecessor_retirement_requires_valid_exact_match_and_elapsed_action(self):
        action = {
            "ticker": "QNCX", "company": "Quince Therapeutics, Inc.",
            "cik10": "0001662774",
            "status": "SYMBOL CHANGED — OLD TICKER RETIRED",
            "effective_date": "2026-10-12", "source_date": "2026-10-09",
            "source_url": "https://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-724",
            "replacement_ticker": "IRLA",
            "checked_at": "2026-10-26T13:27:11.549+00:00",
        }
        registry = [{k: action[k] for k in ("ticker", "company", "cik10")}]
        now = datetime(2026, 10, 26, 14, tzinfo=timezone.utc)
        self.assertEqual(
            validated_listing_exclusions({"records": [action]}, registry, now),
            {"QNCX": action})
        bads = [
            {"replacement_ticker": "QNCX"},
            {"replacement_ticker": "IRLA|QNCX"},
            {"replacement_ticker": ""},
            {"replacement_ticker": None},
            {"ticker": "IRLA"},
            {"company": "Unrelated issuer"},
            {"cik10": "0001234567"},
            {"effective_date": "2026-10-27"},
            {"source_date": "2026-10-13"},
            {"source_url": "http://www.nasdaqtrader.com/TraderNews.aspx?id=ECA2026-724"},
            {"source_url": "https://www.nasdaqtrader.com.evil.test/TraderNews.aspx?id=ECA2026-724"},
            {"status": "SYMBOL CHANGE ANNOUNCED"},
        ]
        for changed in bads:
            with self.subTest(changed=changed):
                self.assertEqual(validated_listing_exclusions(
                    {"records": [{**action, **changed}]}, registry, now), {})
        self.assertEqual(validated_listing_exclusions({"records": [action, action]},
                         registry, now), {})
        self.assertEqual(validated_listing_exclusions({"records": [action]},
                         registry, datetime(2026, 10, 11, 14, tzinfo=timezone.utc)), {})

    def test_qncx_historical_trial_survives_without_current_listing_or_successor(self):
        notice = json.loads((Path(__file__).resolve().parents[1]
                             / "data/phase_pipeline_listing_exclusions.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reg = [{"ticker": "QNCX", "company": "Quince Therapeutics, Inc.",
                    "cik10": "0001662774"}]
            for name, fields, rows in (
                ("company_registry.csv", list(reg[0]), reg),
                ("phase_pipeline.csv", COLUMNS, [{
                    "ticker": "QNCX", "company": "Quince Therapeutics, Inc.",
                    "nct_id": "NCT87654321", "program_key": "QNCX|legacy trial|disease",
                    "phases": "PHASE2",
                }]),
            ):
                with (root / name).open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
            (root / "phase_pipeline_listing_exclusions.json").write_text(json.dumps(notice))
            with patch("scripts.phase_pipeline.datetime") as clock, \\
                    patch("requests.Session") as session, \\
                    patch("scripts.phase_pipeline.fetch_market_caps", return_value=[]) as fetch:
                clock.now.return_value = datetime(2026, 10, 26, 14, tzinfo=timezone.utc)
                session.return_value.get.return_value.json.return_value = {"studies": []}
                state = scan(root)
            fetch.assert_called_once_with(set())
            self.assertEqual(state["market_cap_listing_excluded_tickers"], 1)
            row = read_rows(root / "phase_pipeline.csv")[0]
            self.assertEqual(row["ticker"], "QNCX")
            self.assertEqual(row["nct_id"], "NCT87654321")
            self.assertEqual(row["market_cap_status"], "NOT_LISTED")
            self.assertEqual(row["market_cap"], "")
            self.assertEqual(row["universe_gate"], "FAIL")
            self.assertNotIn("IRLA", str(row))

    def test_collector_skips_retired_quote_and_retains_historical_trial(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, fields, rows in (
                ("company_registry.csv", list(REGISTRY[0]), REGISTRY),
                ("phase_pipeline.csv", COLUMNS,
                 [{"ticker": "TBPH", "company": RECORD["company"], "nct_id": "NCT12345678",
                   "program_key": "TBPH|old drug|disease", "phases": "PHASE2"}]),
            ):
                with (root / name).open("w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
            (root / "phase_pipeline_listing_exclusions.json").write_text(json.dumps({"records": [RECORD]}))
            with patch("scripts.phase_pipeline.datetime") as clock, patch("requests.Session") as session, \
                    patch("scripts.phase_pipeline.fetch_market_caps", return_value=[]) as fetch:
                clock.now.return_value = NOW
                session.return_value.get.return_value.json.return_value = {"studies": []}
                state = scan(root)
            fetch.assert_called_once_with(set())
            self.assertEqual(state["status"], "COMPLETE")
            self.assertEqual(state["market_cap_source_unavailable"], 0)
            self.assertEqual(state["market_cap_listing_excluded_tickers"], 1)
            saved = read_rows(root / "phase_pipeline.csv")
            self.assertEqual(len(saved), 1)
            self.assertEqual(saved[0]["market_cap_status"], "NOT_LISTED")
            self.assertEqual(saved[0]["market_cap"], "")
            self.assertEqual(saved[0]["universe_gate"], "FAIL")
