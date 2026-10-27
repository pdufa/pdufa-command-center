"""Exercise scan-launch and alert-routing boundaries without network access."""
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import adhoc_alert_check as alerts
from scripts.pdufa_auto_repair import decide

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github/workflows"


class ScanLaunchTests(unittest.TestCase):
    def test_saved_settings_match_the_active_clock_and_stage_names(self):
        config = json.loads((ROOT / "config/scan_234.json").read_text())
        schedule = config["clinical_source_schedule"]
        self.assertEqual(schedule["pacific_daylight_time"], "22:00")
        self.assertEqual(schedule["pacific_standard_time"], "22:00")
        launcher = (WORKFLOWS / "pdufa-nightly-pacific-start.yml").read_text()
        self.assertEqual(schedule["cron_utc"], re.findall(r"^\s+- cron: '([^']+)'", launcher, re.M))
        self.assertEqual([tab["name"] for tab in config["tabs"]],
                         ["PIPELINE", "PIPELINE - clinical enrichment", "GEM JR"])
        self.assertFalse(config["automation_enabled"])
        self.assertEqual(config["baseline_state"], "NOT_VERIFIED")

    def run_dispatch(self, mode, action, fail=False):
        workflow = (WORKFLOWS / "pdufa-nightly-pacific-start.yml").read_text()
        step = workflow.split("- name: Dispatch the entire awaited sequence", 1)[1]
        script = textwrap.dedent(step.split("run: |\n", 1)[1]
                                 .split("\n      - name:", 1)[0])
        # GitHub evaluates recovery-aware expressions before invoking bash.
        # Exercise the ordinary Pacific admission path with neither one-time
        # recovery override set; leave the real launcher unchanged.
        def expression(match):
            value = match.group()
            if "steps.pacific.outputs.scan_mode" in value:
                return mode
            if "steps.pacific.outputs.gem_action" in value:
                return action
            raise AssertionError("Unexpected launcher expression: " + value)
        script = re.sub(r"\$\{\{[^}]+\}\}", expression, script)
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            capture = folder / "request.json"
            gh = folder / "gh"
            gh.write_text("#!" + sys.executable + "\n" + textwrap.dedent(r'''
                import json, os, re, sys
                args = sys.argv[1:]
                assert args[:2] == ["api", "--method"] and args[2] == "POST"
                assert args[3].endswith("/pdufa-overnight-sequential.yml/dispatches")
                body = {}
                for index, argument in enumerate(args):
                    if argument != "-f":
                        continue
                    key, value = args[index + 1].split("=", 1)
                    nested = re.fullmatch(r"inputs\[([^\]]+)\]", key)
                    if nested:
                        body.setdefault("inputs", {})[nested.group(1)] = value
                    else:
                        body[key] = value
                with open(os.environ["GH_CAPTURE"], "w") as output:
                    json.dump(body, output)
                if set(body) != {"ref", "inputs"} or body["ref"] != "main":
                    sys.exit(22)
                if os.environ.get("SIMULATE_GH_FAILURE") == "1":
                    sys.exit(23)
                '''))
            gh.chmod(0o700)
            result = subprocess.run(
                ["bash", "-c", script], text=True, capture_output=True,
                timeout=10, env={**os.environ, "PATH": directory + os.pathsep + os.environ["PATH"],
                                "GH_CAPTURE": str(capture), "GH_TOKEN": "synthetic-token",
                                "GITHUB_REPOSITORY": "pdufa/pdufa-command-center",
                                "SIMULATE_GH_FAILURE": "1" if fail else "0"},
            )
            return result, json.loads(capture.read_text())

    def test_actual_launcher_step_sends_github_dispatch_inputs(self):
        for mode, action in (("DELTA", "REVERIFY_PARTIAL"), ("FULL", "RESCAN_ALL")):
            with self.subTest(mode=mode):
                result, body = self.run_dispatch(mode, action)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(body, {"ref": "main", "inputs": {
                    "scan_mode": mode, "gem_action": action}})

    def test_failed_dispatch_is_not_reported_as_requested(self):
        result, _ = self.run_dispatch("DELTA", "REVERIFY_PARTIAL", fail=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Requested ALL", result.stdout)


class RepairRoutingTests(unittest.TestCase):
    def test_renamed_pipeline_acceptance_is_monitored_and_eligible(self):
        name = (WORKFLOWS / "prephase3-acceptance.yml").read_text().splitlines()[0][6:]
        repair = (WORKFLOWS / "pdufa-safe-auto-repair.yml").read_text()
        self.assertIn("- '" + name + "'", repair)
        sha = "f" * 40
        run = {"id": 1, "name": name, "status": "completed", "conclusion": "failure",
               "run_attempt": 1, "head_branch": "main", "head_sha": sha, "event": "push"}
        args = (run, [{"conclusion": "failure"}], "ConnectionResetError", sha, None,
                datetime(2026, 10, 16, tzinfo=timezone.utc))
        self.assertEqual(decide(*args)[0], "rerun")
        self.assertEqual(decide({**run, "run_attempt": 2}, *args[1:])[0], "skip")


class FiledAlertAuditTests(unittest.TestCase):
    def audit(self, count=1, missing=None):
        client = Mock()
        selected = []
        current = [None]

        def select(folder, readonly=False):
            selected.append((folder, readonly))
            current[0] = folder
            return ("NO", []) if folder == missing else ("OK", [b"1"])

        fetched_batches = []

        def uid(operation, *args):
            if operation == "SEARCH":
                ids = b" ".join(str(i).encode() for i in range(1, count + 1))
                return "OK", [ids if current[0] in ('"PDUFA"', '"PDUFA/Scan ERROR"') else b""]
            if operation == "FETCH":
                batch = args[0].split(b",")
                fetched_batches.append((current[0], batch))
                if not 1 <= len(batch) <= 100:
                    raise AssertionError("IMAP header request exceeds 100 messages")
                if "BODY.PEEK" not in args[1]:
                    raise AssertionError("Non-read-only header fetch")
                header = (b"Subject: [pdufa/pdufa-command-center] workflow failed\r\n"
                          b"Date: Thu, 15 Oct 2026 19:00:00 +0000\r\n"
                          b"Message-ID: <one-alert@example.test>\r\n\r\n")
                return "OK", [
                    (b"1 (UID " + uid + b" X-GM-MSGID 123456 BODY[HEADER] {160}", header)
                    for uid in batch
                ]
            raise AssertionError("Audit attempted a mailbox mutation: " + operation)

        client.select.side_effect = select
        client.uid.side_effect = uid
        with patch.object(alerts.imaplib, "IMAP4_SSL", return_value=client):
            report = alerts.audit_gmail("synthetic@example.test", "synthetic-password",
                                        datetime(2026, 10, 15, tzinfo=timezone.utc))
        return report, selected, client, fetched_batches

    def test_archived_alerts_are_read_once_across_parent_and_subfolders(self):
        report, selected, client, batches = self.audit()
        self.assertEqual(report["status"], "CHECKED")
        self.assertEqual(report["error_subjects"], 1)
        self.assertEqual(report["relevant_messages"], 1)
        for label in ("PDUFA", "PDUFA/Scan START", "PDUFA/Scan END", "PDUFA/Scan ERROR",
                      "PDUFA/Daily Report", "PDUFA/Weekly Report"):
            self.assertIn(('"' + label + '"', True), selected)
        self.assertTrue(all(readonly for _, readonly in selected))
        for call in client.uid.call_args_list:
            if call.args[0] == "FETCH":
                self.assertIn("BODY.PEEK", call.args[2])

    def test_unreadable_pdufa_folder_remains_incomplete(self):
        report, _, _, _ = self.audit(missing='"PDUFA/Scan ERROR"')
        self.assertEqual(report["status"], "PARTIAL")
        self.assertIn("Scan ERROR", report["reason"])

    def test_more_than_150_headers_are_checked_in_100_message_batches(self):
        report, selected, client, batches = self.audit(count=251)
        self.assertEqual(report["status"], "CHECKED")
        self.assertEqual(report["error_subjects"], 1)
        self.assertEqual(report["relevant_messages"], 1)
        for label in ('"PDUFA"', '"PDUFA/Scan ERROR"'):
            sizes = [len(uids) for folder, uids in batches if folder == label]
            self.assertEqual(sizes, [100, 100, 51])
        self.assertTrue(all(readonly for _, readonly in selected))


if __name__ == "__main__":
    unittest.main()
