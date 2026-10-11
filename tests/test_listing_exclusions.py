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
