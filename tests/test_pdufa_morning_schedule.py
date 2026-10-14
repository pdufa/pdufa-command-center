"""GitHub can queue a 6 AM PST/PDT cron for hours; delayed reports must not disappear."""
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/pdufa-morning-6am-results.yml"


class MorningCronTests(unittest.TestCase):
    def test_late_cron_runs_same_morning_and_wrong_offset_skips(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        block = workflow.split("      - name: Check scheduled Pacific morning slot", 1)[1]
        block = block.split("      - uses: actions/checkout@v4", 1)[0]
        script = textwrap.dedent(block.split("        run: |\n", 1)[1])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stub = root / "date"
            stub.write_text(
                "#!/bin/sh\n"
                'case "$1" in\n'
                '  +%H) echo "$MOCK_LOCAL_HOUR";;\n'
                '  +%z) echo "$MOCK_LOCAL_OFFSET";;\n'
                '  *) exit 2;;\n'
                "esac\n", encoding="utf-8",
            )
            stub.chmod(0o755)
            cases = [
                ("06", "-0700", "0 13 * * *", 0, "run=true"),
                ("11", "-0700", "15 13 * * *", 0, "run=true"),
                ("12", "-0800", "0 14 * * *", 0, "run=true"),
                ("06", "-0800", "0 13 * * *", 0, "run=false"),
                ("13", "-0700", "0 13 * * *", 1, ""),
                ("05", "-0800", "0 14 * * *", 1, ""),
            ]
            for hour, offset, cron, returncode, output in cases:
                with self.subTest(hour=hour, offset=offset, cron=cron):
                    path = root / "output"
                    path.write_text("", encoding="utf-8")
                    env = {
                        **os.environ, "PATH": str(root) + os.pathsep + os.environ["PATH"],
                        "MOCK_LOCAL_HOUR": hour,
                        "MOCK_LOCAL_OFFSET": offset,
                        "CRON_SLOT": cron,
                        "EVENT_NAME": "schedule", "GITHUB_OUTPUT": str(path),
                    }
                    result = subprocess.run(
                        ["bash", "-c", script], env=env,
                        text=True, capture_output=True, timeout=10,
                    )
                    self.assertEqual(result.returncode, returncode, result.stderr)
                    self.assertIn(output, path.read_text(encoding="utf-8"))

    def test_no_silent_green_skip_and_no_rebase_deadlock(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("::error::6 AM Pacific scheduled slot arrived outside", workflow)
        self.assertIn("::warning::6 AM Pacific GitHub cron arrived late", workflow)
        self.assertIn("git rebase --abort || true", workflow)
        self.assertIn("pdufa_am_6am_results.json", workflow)
        self.assertIn("snapshot_date_pacific", workflow)


if __name__ == "__main__":
    unittest.main()
