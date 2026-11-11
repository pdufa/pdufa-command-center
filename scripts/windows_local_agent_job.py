#!/usr/bin/env python3
"""Run the guarded local proposal test and publish only a redacted status to GitHub.

No generated code is executed, applied, committed, pushed or deployed.
Repository issue 1096 is PUBLIC: publish only generic status, never logs,
file paths, prompts, scientific evidence, machine details or credentials.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path.home() / "PDUFA-Agent-Reports"
CONTROLLER = ROOT / "scripts/windows_local_agent_controller.py"
REPO = "pdufa/pdufa-command-center"
ISSUE = "1096"


def main() -> int:
    started = time.time()
    print("Running guarded local PDUFA proposal check ...")
    try:
        run = subprocess.run(
            [sys.executable, str(CONTROLLER)], cwd=ROOT,
            capture_output=True, text=True, errors="replace", timeout=900,
        )
        controller_ok = run.returncode == 0
        print("Local controller:", "PASS" if controller_ok else "FAILED")
    except (OSError, subprocess.TimeoutExpired) as exc:
        controller_ok = False
        print("Local controller could not finish:", type(exc).__name__)

    # Do not report success based on an old or unrelated report.
    reports = sorted(REPORTS.glob("status-*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if REPORTS.exists() else []
    verified = False
    if controller_ok and reports and reports[0].stat().st_mtime >= started - 2:
        try:
            record = json.loads(reports[0].read_text(encoding="utf-8"))
            verified = (record.get("state") == "proposal_for_review"
                        and record.get("audit_passed") is True
                        and record.get("production_modified") is False)
        except (OSError, ValueError):
            pass

    status = "PASS — a new read-only proposal was generated" if verified else "NEEDS ATTENTION — no verified new proposal"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        "# Windows PDUFA local agent — remote status\n\n"
        f"**Last reported:** {timestamp}\n\n"
        f"**Status:** {status}\n\n"
        "**Mode:** Read-only AI development proposals\n\n"
        "**Safety:** Production edits, commits, deploys, and automated code changes are disabled.\n\n"
        "**Scientific assessment levels:** No implementation or completion is implied by this report.\n\n"
        "**Privacy:** This is a public issue with generic status only. No scientific files, prompts, "
        "local paths, error logs, credentials, or machine details are posted.\n\n"
        "If the status becomes stale, the Windows computer may be offline, asleep, signed out, "
        "or unable to reach GitHub.\n"
    )
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "last-run-summary.json").write_text(json.dumps({
        "timestamp_utc": timestamp, "local_proposal_ok": verified,
        "remote_report_target": f"https://github.com/{REPO}/issues/{ISSUE}",
    }, indent=2) + "\n", encoding="utf-8")
    filename = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md", prefix="pdufa-status-",
            delete=False
        ) as tmp:
            filename = Path(tmp.name)
            tmp.write(body)
        result = subprocess.run(
            ["gh", "issue", "edit", ISSUE, "--repo", REPO, "--body-file", str(filename)],
            cwd=ROOT, capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            print("Remote GitHub status updated: https://github.com/" + REPO + "/issues/" + ISSUE)
        else:
            print("WARNING: GitHub status not updated. Check 'gh auth status' and internet.")
    except (OSError, subprocess.TimeoutExpired):
        print("WARNING: Remote status not updated.")
    finally:
        if filename is not None:
            filename.unlink(missing_ok=True)
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
