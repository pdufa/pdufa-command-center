"""Guarded post-scan workflow repair, *after* scoring and Gmail/GitHub audit.

Only failed-job reruns for independently proven transient GitHub faults on the
current main SHA. No edits to scientific data, emails, stocks or scanner code.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from pdufa_auto_repair import RERUN_ALLOWLIST, decide


def gh(*args):
    result = subprocess.run(["gh", *args], capture_output=True, text=True,
                            timeout=35, check=False)
    if result.returncode:
        raise RuntimeError("GitHub call failed: " + " ".join(args[:3]))
    return result.stdout


def candidates(alerts: dict) -> list[int]:
    """Ignore past and non-GitHub failures; never include source collectors."""
    if alerts.get("github", {}).get("status") == "UNAVAILABLE":
        return []
    entries = alerts.get("github", {}).get("current_failures", [])
    ids = []
    for item in entries:
        if not isinstance(item, dict):
            continue
        run_id = item.get("id")
        if type(run_id) is int and run_id > 0 and item.get("workflow", "").endswith(".yml"):
            ids.append(run_id)
    return list(dict.fromkeys(ids))[:12]


def repair_current_failures(alerts: dict, *, repo: str, current_sha: str,
                            manifest: dict | None = None) -> dict:
    from datetime import datetime, timezone
    decisions = []
    for run_id in candidates(alerts):
        decision = {"run_id": run_id, "action": "skip", "reason": ""}
        try:
            run = json.loads(gh("api", f"repos/{repo}/actions/runs/{run_id}"))
            if run.get("name") not in RERUN_ALLOWLIST:
                decision["reason"] = "Not on bounded repair allowlist."
                decisions.append(decision)
                continue
            jobs = json.loads(gh("api", f"repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"))
            # Fail-closed on unreadable/truncated logs. Never execute the logs.
            logs = gh("run", "view", str(run_id), "--repo", repo, "--log-failed")
            if len(logs) > 150_000:
                decision["reason"] = "Failure logs too large to classify safely."
                decisions.append(decision)
                continue
            action, reason = decide(run, jobs.get("jobs", []), logs, current_sha,
                                    manifest, datetime.now(timezone.utc))
            decision.update(action=action, reason=reason)
            if action == "rerun":
                gh("run", "rerun", str(run_id), "--repo", repo, "--failed")
                decision["action"] = "rerun_requested"
            elif action == "refresh_pre3":
                # PRE3 refresh policy depends on extra duplicate-run checks in
                # the dedicated auto-repair workflow; do not skip those guards.
                decision.update(action="skip", reason="PRE3 refresh requires dedicated guarded workflow.")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            decision.update(action="skip", reason="Could not safely verify or request repair: "
                            + type(exc).__name__)
        decisions.append(decision)
    return {
        "scope": "Source-preserving post-scan repair attempts after scoring and error checks",
        "decisions": decisions,
        "rerun_requests": sum(d["action"] == "rerun_requested" for d in decisions),
        "note": "Rerun request does not prove subsequent success. No clinical or market data were repaired.",
    }


def main() -> None:
    alert_file = Path(os.environ.get("PDUFA_ALERT_REPORT", "reports/adhoc_alert_check.json"))
    output = Path(os.environ.get("PDUFA_REPAIR_REPORT", "reports/post_scan_repair.json"))
    output.parent.mkdir(exist_ok=True, parents=True)
    if not alert_file.is_file():
        result = {"status": "SKIPPED", "reason": "Prior Gmail/GitHub audit artifact missing; never repair blindly."}
    else:
        try:
            alerts = json.loads(alert_file.read_text(encoding="utf-8"))
            repo = os.environ.get("GITHUB_REPOSITORY", "")
            if repo != "pdufa/pdufa-command-center":
                raise ValueError("Untrusted repository identity")
            sha = gh("api", f"repos/{repo}/commits/main", "--jq", ".sha").strip()
            manifest_path = Path("data/step7_live_status.json")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else None
            result = repair_current_failures(alerts, repo=repo, current_sha=sha,
                                              manifest=manifest)
            result["status"] = "CHECKED"
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
            result = {"status": "SKIPPED", "reason": "Failed closed: " + type(exc).__name__}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write("### Post-scan guarded remediation\n\n"
                         + "Status: " + result["status"] + "; rerun requests: "
                         + str(result.get("rerun_requests", 0)) + "\n\n"
                         + "No clinical-data or source-record changes were made.\n")


if __name__ == "__main__":
    main()
