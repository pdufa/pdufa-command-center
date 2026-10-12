"""Contracts for one Pacific nightly start and a strictly serial post-scan chain."""
import re
import unittest
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def read(name):
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def job(text, name):
    match = re.search(r"(?m)^  " + re.escape(name) + r":\s*$", text)
    if match is None:
        raise AssertionError(f"Missing job {name}")
    next_job = re.search(r"(?m)^  [a-z][a-z0-9_-]*:\s*$", text[match.end():])
    return text[match.start(): match.end() + next_job.start() if next_job else len(text)]


class PacificNightlySequenceTests(unittest.TestCase):
    def test_pacific_daylight_and_standard_crons(self):
        scheduler = read("pdufa-nightly-pacific-start.yml")
        self.assertIn("cron: '30 3 * * *'", scheduler)
        self.assertIn("cron: '30 4 * * *'", scheduler)
        self.assertIn("TZ=America/Los_Angeles date +%z", scheduler)
        self.assertIn('"$offset" = -0700', scheduler)
        self.assertIn('"$offset" = -0800', scheduler)
        for utc_hour, month in [(3, 7), (4, 1)]:
            date = datetime(2026, month, 15, utc_hour, 30, tzinfo=timezone.utc)
            converted = date.astimezone(ZoneInfo("America/Los_Angeles"))
            self.assertEqual((converted.hour, converted.minute), (20, 30))
        self.assertIn("-f 'inputs[scan]=ALL'", scheduler)

    def test_clinical_runs_in_numbered_order(self):
        clinical = read("pdufa-nightly-clinical.yml")
        self.assertNotIn("\n  schedule:", clinical)
        self.assertIn("workflow_dispatch:", clinical)
        self.assertIn("needs: scan2", job(clinical, "scan3"))
        self.assertIn("needs: scan3", job(clinical, "scan4"))
        self.assertLess(clinical.index("\n  scan2:"), clinical.index("\n  scan3:"))
        self.assertLess(clinical.index("\n  scan3:"), clinical.index("\n  scan4:"))
        for scan in "234":
            part = job(clinical, "scan" + scan)
            self.assertIn(' --scan "' + scan + '"', part)
            self.assertIn("run_scan_with_email.py", part)
            self.assertIn("actions/upload-artifact", part)

    def test_publish_then_five_sources_then_audit(self):
        publisher = read("pdufa-nightly-report.yml")
        self.assertIn('workflows: ["PDUFA Nightly Clinical Scans"]', publisher)
        self.assertNotIn("\n  push:", publisher)
        source = read("pdufa-nightly-missing-sources.yml")
        self.assertIn("workflows: ['PDUFA Nightly Scan Report Publisher']", source)
        self.assertNotIn("\n  schedule:", source)
        expected = ["fda", "sec", "financial", "market", "issuer"]
        for first, second in zip(expected, expected[1:]):
            self.assertIn("needs: source_" + first, job(source, "source_" + second))
        self.assertIn("needs: [source_fda, source_sec, source_financial, source_market, source_issuer]",
                      job(source, "reconcile"))
        for stage in expected:
            segment = job(source, "source_" + stage)
            self.assertIn("run_scan_with_email.py", segment)
            self.assertIn("actions/upload-artifact", segment)
        feed = job(source, "refresh-prephase3")
        self.assertIn("needs: reconcile", feed)
        self.assertIn("uses: ./.github/workflows/step7-live-feed.yml", feed)
        self.assertIn("contents: write", feed)
        standalone_feed = read("step7-live-feed.yml")
        self.assertNotIn("\n  schedule:", standalone_feed)
        self.assertIn("\n  workflow_call:", standalone_feed)

    def test_scoring_and_repair_only_follow_extended_scan(self):
        score = read("pdufa-nightly-scoring-then-repair.yml")
        trigger = score.split("\npermissions:", 1)[0]
        self.assertIn("PDUFA Nightly FDA SEC Financial Market Issuer Sources", trigger)
        self.assertNotIn("\n      - PDUFA Nightly Scan Report Publisher\n", trigger)
        self.assertIn("needs: scoring", job(score, "error-check"))
        self.assertIn("needs: [scoring, error-check]", job(score, "safe-repair"))


if __name__ == "__main__":
    unittest.main()
