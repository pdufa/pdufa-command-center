"""Contracts for one Pacific nightly start and a strictly serial post-scan chain."""
import os
import re
import subprocess
import tempfile
import textwrap
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
        self.assertIn("cron: '0 6 * * *'", scheduler)
        self.assertIn("cron: '0 7 * * *'", scheduler)
        self.assertIn("TZ=America/Los_Angeles date +%z", scheduler)
        self.assertIn('"$offset" = -0700', scheduler)
        self.assertIn('"$offset" = -0800', scheduler)
        # 11 PM Pacific occurs on the PREVIOUS Pacific date versus UTC.
        for utc_hour, month in [(6, 7), (7, 1)]:
            date = datetime(2026, month, 15, utc_hour, 0, tzinfo=timezone.utc)
            converted = date.astimezone(ZoneInfo("America/Los_Angeles"))
            self.assertEqual((converted.hour, converted.minute), (23, 0))
            self.assertEqual(converted.day, 14)
        self.assertIn("-f 'inputs[scan]=ALL'", scheduler)

    def test_delayed_utc_crons_do_not_restart_scans_next_morning(self):
        scheduler = read("pdufa-nightly-pacific-start.yml")
        block = scheduler.split("      - name: Accept only matching 11:00 PM Pacific cron slot", 1)[1]
        block = block.split("      - name: Dispatch clinical scan to start serial chain", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            fake_date = directory / "date"
            fake_date.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                '  +%H) echo "$MOCK_LOCAL_HOUR";;\n'
                '  +%M) echo "$MOCK_LOCAL_MINUTE";;\n'
                '  +%z) echo "$MOCK_LOCAL_OFFSET";;\n'
                '  *) exit 2;;\n'
                "esac\n", encoding="utf-8")
            fake_date.chmod(0o755)
            cases = (
                ("23", "00", "-0700", "0 6 * * *", "run=true"),
                ("23", "15", "-0700", "15 6 * * *", "run=true"),
                ("23", "30", "-0700", "30 6 * * *", "run=true"),
                ("23", "00", "-0800", "0 7 * * *", "run=true"),
                ("23", "30", "-0800", "30 7 * * *", "run=true"),
                ("23", "00", "-0700", "0 7 * * *", "run=false"),
                ("23", "00", "-0800", "0 6 * * *", "run=false"),
                ("00", "05", "-0700", "5 7 * * *", "run=false"),
                ("01", "05", "-0800", "5 9 * * *", "run=false"),
                ("22", "30", "-0700", "30 6 * * *", "run=false"),
                ("06", "00", "-0700", "0 6 * * *", "run=false"),
            )
            for hour, minute, offset, cron, expected in cases:
                with self.subTest(hour=hour, minute=minute, offset=offset, cron=cron):
                    output = directory / "result"
                    output.write_text("", encoding="utf-8")
                    env = {**os.environ, "PATH": str(directory) + os.pathsep + os.environ.get("PATH", ""),
                           "EVENT_NAME": "schedule", "SCHEDULE_CRON": cron,
                           "GITHUB_OUTPUT": str(output), "MOCK_LOCAL_HOUR": hour,
                           "MOCK_LOCAL_MINUTE": minute, "MOCK_LOCAL_OFFSET": offset}
                    process = subprocess.run(["bash", "-c", script], env=env,
                                             capture_output=True, text=True, timeout=10)
                    self.assertEqual(process.returncode, 0, process.stderr)
                    self.assertIn(expected, output.read_text(encoding="utf-8"))

    def test_fallback_start_never_duplicates_tonights_scans(self):
        scheduler = read("pdufa-nightly-pacific-start.yml")
        for cron in ("0 6 * * *", "15 6 * * *", "30 6 * * *", "0 7 * * *", "15 7 * * *", "30 7 * * *"):
            self.assertIn(cron, scheduler)
        self.assertIn("pdufa-clinical-runs.json", scheduler)
        self.assertIn("Nightly clinical scan already started today", scheduler)
        self.assertIn("No duplicate dispatch", scheduler)
        self.assertIn('inputs[scan]=ALL', scheduler)

    def test_publisher_and_extended_source_watchdogs_are_guarded(self):
        scheduler = read("pdufa-nightly-pacific-start.yml")
        for cron in ("5 7 * * *", "35 7 * * *", "5 8 * * *", "35 8 * * *",
                     "5 9 * * *", "35 9 * * *"):
            self.assertIn(cron, scheduler)
        # Overnight recovery is anchored to the PREVIOUS night's 11 PM start.
        self.assertIn("(local - timedelta(days=1)).replace(hour=23", scheduler)
        self.assertIn("(la - timedelta(days=1)).replace(hour=23", scheduler)
        self.assertIn("Recover missing clinical report publishing handoff", scheduler)
        self.assertIn("Recover missing extended-source verification handoff", scheduler)
        self.assertIn("Report publisher already started after this clinical scan", scheduler)
        self.assertIn("Extended verification run already exists; skip duplicate", scheduler)
        self.assertIn('publisher.get("conclusion") != "success"', scheduler)
        self.assertIn('latest_clinical.get("conclusion") != "success"', scheduler)
        self.assertIn("timedelta(minutes=2)", scheduler)
        self.assertIn("pdufa-nightly-missing-sources.yml/dispatches", scheduler)
        self.assertIn("Dispatch does not establish source verification or completion.", scheduler)

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
