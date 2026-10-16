"""Regression checks for the full-width GEM stage workbenches."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from gem_stage_dossier import exact_event, scan_health, source_date, timeline_events


class StageDossierTests(unittest.TestCase):
    def test_strict_iso_dates(self):
        self.assertEqual(source_date("2026-10-15T11:22:33Z"), date(2026, 10, 15))
        self.assertIsNone(source_date(""))
        self.assertIsNone(source_date("unknown"))

    def test_dead_zone_uses_exact_program_dates_only(self):
        event = {"phase3_date": "2026-02-01", "pdufa_date": "2026-12-01"}
        record = {"First close": "2026-03-12", "Second close": "2026-05-05"}
        rows, status = timeline_events(record, event, date(2026, 10, 15))
        self.assertEqual(rows[1]["Days from readout"], 39)
        self.assertEqual(rows[2]["Days from readout"], 93)
        self.assertIn("47 days to reported PDUFA", status)

    def test_no_invented_dead_zone_without_readout(self):
        rows, status = timeline_events({"PDUFA saved": "2026-12-01"}, {},
                                      date(2026, 10, 15))
        self.assertEqual(rows[0]["Saved date"], "NOT AVAILABLE")
        self.assertIn("cannot be calculated", status)

    def test_ambiguous_event_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pdufa_candidates.csv"
            path.write_text(
                "event_key,ticker,phase3_date\nX|1,AAA,2026-02-01\n"
                "X|1,BBB,2026-03-01\n", encoding="utf-8")
            self.assertEqual(exact_event(tmp, "X|1"), {})
            self.assertEqual(exact_event(tmp, "TRIAL|AAA|NCT12345678"), {})
            path.write_text(
                "event_key,ticker,phase3_date\nX|1,AAA,2026-02-01\n",
                encoding="utf-8")
            self.assertEqual(exact_event(tmp, "X|1")["ticker"], "AAA")

    def test_scan_report_does_not_claim_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "nightly_scan_report.json").write_text(
                json.dumps({"status": "PARTIAL",
                            "verification": {"all_source_coverage": "NOT_VERIFIED"}}),
                encoding="utf-8")
            health = scan_health(tmp)
            self.assertEqual(health[0]["Published status"], "PARTIAL")
            self.assertEqual(health[0]["Coverage"], "NOT_VERIFIED")
            self.assertEqual(health[1]["Published status"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
