#!/usr/bin/env python3
"""Run guarded proposals, sandbox drafts, regression tests and FOCUS gap queue.

No generated code is executed, applied, committed, pushed or deployed.
Repository issue 1096 is PUBLIC: publish only generic status, never logs,
file paths, prompts, scientific evidence, machine details or credentials.
"""
from __future__ import annotations

from datetime import datetime, timezone
from windows_local_agent_focus_validation import verify_queue_report, verify_registry_research_report
from windows_local_agent_live_status import verify_live_summary
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
REPORTS = Path.home() / "PDUFA-Agent-Reports"
CONTROLLER = ROOT / "scripts/windows_local_agent_controller.py"
DRAFT_CONTROLLER = ROOT / "scripts/windows_local_agent_code_draft.py"
REGRESSION_GATE = ROOT / "scripts/windows_local_agent_regression.py"
FOCUS_QUEUE = ROOT / "scripts/level2_focus_evidence_queue.py"
FOCUS_SNAPSHOT = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
REGISTRY_RESEARCH = ROOT / "scripts/level2_focus_registry_research.py"
REGISTRY_SCAN = ROOT / "new-platform/frontend/data/focus-29-registry-source-scan-20261108.json"
LIVE_CAPTURE = ROOT / "scripts/windows_local_agent_live_focus_registry.py"
LIVE_RECEIPTS = REPORTS / "level2-live-registry-captures"
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

    # The coding draft stays OUTSIDE the Git checkout. Never run generated source.
    # Even if the prose proposal fails, attempt the bounded sandbox draft; its
    # own mandatory RAAS audit gate will stop it if the policy is not satisfied.
    draft_started = time.time()
    try:
        draft_run = subprocess.run(
            [sys.executable, str(DRAFT_CONTROLLER)], cwd=ROOT,
            capture_output=True, text=True, errors="replace", timeout=900,
        )
        draft_command_ok = draft_run.returncode == 0
        print("Sandbox code draft:", "PASS" if draft_command_ok else "FAILED")
    except (OSError, subprocess.TimeoutExpired) as exc:
        draft_command_ok = False
        print("Sandbox code draft could not finish:", type(exc).__name__)

    draft_verified = False
    draft_reports = (
        sorted(REPORTS.glob("code-draft-status-*.json"),
               key=lambda p: p.stat().st_mtime, reverse=True)
        if REPORTS.exists() else []
    )
    if (draft_command_ok and draft_reports
            and draft_reports[0].stat().st_mtime >= draft_started - 2):
        try:
            draft_record = json.loads(
                draft_reports[0].read_text(encoding="utf-8")
            )
            draft_verified = (
                draft_record.get("state") == "sandbox_draft_for_review"
                and draft_record.get("syntax_check") == "pass"
                and draft_record.get("production_changed") is False
                and draft_record.get("repository_changed") is False
                and draft_record.get("generated_source_executed") is False
            )
        except (OSError, ValueError):
            pass

    # Run the Level 1 and Level 2 evidence-safety regression suites.
    # A failure prevents any all-green remote report.
    try:
        regression = subprocess.run(
            [sys.executable, "-B", str(REGRESSION_GATE)], cwd=ROOT,
            capture_output=True, text=True, errors="replace", timeout=600,
        )
        regression_ok = regression.returncode == 0
        print("Level 1–2 regression gate:", "PASS" if regression_ok else "FAILED")
    except (OSError, subprocess.TimeoutExpired) as exc:
        regression_ok = False
        print("Level 1–2 regression gate unavailable:", type(exc).__name__)

    # Rebuild the local, research-only evidence-gap queue after successful
    # regression tests. Verify a NEW report against the exact FOCUS snapshot
    # bytes; old reports and claims of completed science must never pass.
    focus_verified = False
    if regression_ok:
        focus_started = time.time()
        try:
            queue_run = subprocess.run(
                [sys.executable, "-B", str(FOCUS_QUEUE)], cwd=ROOT,
                capture_output=True, text=True, errors="replace", timeout=300,
            )
            focus_command_ok = queue_run.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            focus_command_ok = False
            print("FOCUS Level 2 queue unavailable:", type(exc).__name__)
        if focus_command_ok:
            try:
                reports = sorted(
                    REPORTS.glob("level2-focus-evidence-queue-*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True,
                )
                if reports and reports[0].stat().st_mtime >= focus_started - 2:
                    report = json.loads(reports[0].read_text(encoding="utf-8"))
                    focus_verified = verify_queue_report(
                        report, FOCUS_SNAPSHOT.read_bytes()
                    )
            except (OSError, ValueError):
                pass
    else:
        print("FOCUS Level 2 queue: SKIPPED — regression failure")
    print("FOCUS Level 2 saved-snapshot queue:", "PASS" if focus_verified else "FAILED")

    # Build research notes only from existing saved ClinicalTrials.gov fields.
    # Never claim a current live registry check or independent FDA judgement.
    research_verified = False
    if regression_ok and focus_verified:
        research_started = time.time()
        try:
            research_run = subprocess.run(
                [sys.executable, "-B", str(REGISTRY_RESEARCH)], cwd=ROOT,
                capture_output=True, text=True, errors="replace", timeout=300,
            )
            research_command_ok = research_run.returncode == 0
        except (OSError, subprocess.TimeoutExpired) as exc:
            research_command_ok = False
            print("Saved registry research unavailable:", type(exc).__name__)
        if research_command_ok:
            try:
                reports = sorted(
                    REPORTS.glob("level2-registry-hypothesis-research-*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True,
                )
                if reports and reports[0].stat().st_mtime >= research_started - 2:
                    research_report = json.loads(
                        reports[0].read_text(encoding="utf-8")
                    )
                    research_verified = verify_registry_research_report(
                        research_report, FOCUS_SNAPSHOT.read_bytes(),
                        REGISTRY_SCAN.read_bytes(),
                    )
            except (OSError, ValueError):
                pass
    else:
        print("Saved registry research: SKIPPED — prior safety gate failed")
    print("Level 2 saved registry research:", "PASS" if research_verified else "FAILED")

    # Bounded unattended HTTPS refresh, on the SAVED roster only.
    # At most 10 primary-registry requests per scheduled run; the 24-hour
    # source cache prevents re-downloading fresh receipts unnecessarily.
    # A partial batch is NOT an independent science review or FDA prediction.
    live_verified = False
    live_fresh = 0
    live_total = 0
    live_failures = 0
    if regression_ok and focus_verified and research_verified:
        live_started = time.time()
        try:
            live_run = subprocess.run(
                [sys.executable, "-B", str(LIVE_CAPTURE), "--batch-size", "10"],
                cwd=ROOT, capture_output=True, text=True,
                errors="replace", timeout=300,
            )
            # Exit code 1 means partial network failure, with a local report.
            # Independently validate the report even in that case.
            live_finished = live_run.returncode in (0, 1)
        except (OSError, subprocess.TimeoutExpired) as exc:
            live_finished = False
            print("Live registry capture unavailable:", type(exc).__name__)
        if live_finished:
            try:
                live_reports = sorted(
                    REPORTS.glob("level2-registry-live-status-*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True,
                )
                if live_reports and live_reports[0].stat().st_mtime >= live_started - 2:
                    latest_live = json.loads(
                        live_reports[0].read_text(encoding="utf-8")
                    )
                    live_verified = verify_live_summary(
                        latest_live, FOCUS_SNAPSHOT.read_bytes(), LIVE_RECEIPTS
                    )
                    if live_verified:
                        live_fresh = latest_live["fresh_exact_registry_captures"]
                        live_total = latest_live["saved_roster_size"]
                        live_failures = latest_live["failed_attempts_this_run"]
            except (OSError, ValueError):
                pass
    else:
        print("Live registry refresh: SKIPPED — prior safety gate failed")
    if not live_verified:
        print("FOCUS live registry refresh: FAILED — invalid or missing report")
    elif live_failures:
        print("FOCUS live registry refresh: NEEDS ATTENTION — retrieval errors")
    elif live_fresh < live_total:
        print("FOCUS live registry refresh: PARTIAL", live_fresh, "of", live_total)
    else:
        print("FOCUS live registry refresh: PASS", live_fresh, "of", live_total)

    if not regression_ok:
        status = "NEEDS ATTENTION — Level 1–2 regressions failed"
    elif not focus_verified:
        status = "NEEDS ATTENTION — saved FOCUS queue failed"
    elif not research_verified:
        status = "NEEDS ATTENTION — saved registry-field research failed"
    elif not live_verified or live_failures:
        status = "NEEDS ATTENTION — live registry refresh failed or is unverifiable"
    elif live_fresh < live_total:
        status = "PARTIAL — live source refresh incomplete; no scientific outcomes"
    elif verified and draft_verified:
        status = "PASS — local proposals, tests and saved FOCUS source refresh"
    elif verified or draft_verified:
        status = "PARTIAL — source refresh passed; one local AI task needs attention"
    else:
        status = "NEEDS ATTENTION — live sources pass, but no new AI output"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = (
        "# Windows PDUFA local agent — remote status\n\n"
        f"**Last reported:** {timestamp}\n\n"
        f"**Status:** {status}\n\n"
        "**Mode:** Read-only proposals, sandbox drafts, regression tests, and saved-snapshot FOCUS evidence-gap queue\n\n"
        "**Safety:** AI-generated code is never executed. Production edits, commits, deploys, and automated repository changes are disabled.\n\n"
        f"**Level 1–2 regression checks:** {'PASS' if regression_ok else 'NEEDS ATTENTION'} (local testing only)\n\n"
        f"**Level 2 saved FOCUS queue:** {'PASS' if focus_verified else 'NEEDS ATTENTION'} (unverified source leads, no live FOCUS verification or scientific predictions)\n\n"
        f"**Level 2 saved registry-field research:** {'PASS' if research_verified else 'NEEDS ATTENTION'} (saved field summaries; no live collection, science verdicts or FDA predictions)\n\n"
        f"**Live saved-FOCUS registry coverage:** {live_fresh}/{live_total if live_verified else 0} "
        f"({'PASS' if live_verified and live_failures == 0 and live_fresh == live_total else 'PARTIAL' if live_verified and live_failures == 0 else 'NEEDS ATTENTION'}). "
        "At most 10 records refreshed per four-hour run; 24-hour cache; source-only, no independent scientific verification.\n\n"
        "**Scientific assessment levels:** No implementation or completion is implied by this report.\n\n"
        "**Privacy:** This is a public issue with generic status only. No scientific files, prompts, "
        "local paths, error logs, credentials, or machine details are posted.\n\n"
        "If the status becomes stale, the Windows computer may be offline, asleep, signed out, "
        "or unable to reach GitHub.\n"
    )
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / "last-run-summary.json").write_text(json.dumps({
        "timestamp_utc": timestamp, "local_proposal_ok": verified,
        "local_sandbox_draft_ok": draft_verified,
        "level1_regression_ok": regression_ok,
        "level2_regression_ok": regression_ok,
        "level2_focus_queue_ok": focus_verified,
        "level2_registry_research_ok": research_verified,
        "level2_live_registry_report_verified": live_verified,
        "level2_live_registry_fresh": live_fresh,
        "level2_live_registry_total": live_total,
        "level2_live_registry_errors": live_failures,
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
    return 0 if verified and draft_verified and regression_ok and focus_verified and research_verified and live_verified and live_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
