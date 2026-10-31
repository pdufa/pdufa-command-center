"""Conservative fail-closed GitHub Actions repair planner; no source evidence mutation."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
RERUN_ALLOWLIST = frozenset({
    "PDUFA Command Center CI",
    "Unified Dashboard Smoke Check",
    "PDUFA Nightly Report Checks",
    "PDUFA Extended Source Scan Tests",
    "PDUFA Nightly Scan Report Publisher",
    "Step 7 PRE PHASE 3 Live Feed",
})
COLLECTOR_BLOCKLIST = frozenset({
    "PDUFA Nightly Clinical Scans",
    "PDUFA Nightly FDA SEC Financial Market Issuer Sources",
    "PDUFA One-Time Clinical Scan",
    "PDUFA Clinical Scan Completion Email",
})
TRANSIENT = (
    r"\b(?:HTTP|status(?: code)?)\s*(?:502|503|504)\b",
    r"\b(?:ConnectTimeout|ReadTimeout|ConnectionResetError|ConnectionAbortedError)\b",
    r"\bconnection (?:reset by peer|timed out|temporarily refused)\b",
    r"\bTemporary failure in name resolution\b",
    r"\b(?:ERR_TIMED_OUT|ERR_CONNECTION_RESET|ERR_NAME_NOT_RESOLVED)\b",
    r"\b(?:TLS handshake timeout|context deadline exceeded|i/o timeout)\b",
    r"\b(?:Service Unavailable|Bad Gateway|Gateway Timeout)\b",
)
PERMANENT = (
    r"\b(?:AssertionError|SyntaxError|IndentationError|ModuleNotFoundError|ImportError|NameError)\b",
    r"^\s*FAIL: test_",
    r"^\s*ERROR: test_",
    r"\bFAILED \(failures=",
    r"\b(?:401|403) (?:Forbidden|Unauthorized)\b",
    r"\bpermission denied\b",
    r"\bResource not accessible by integration\b",
    r"\b(?:invalid credentials|secret .* missing|missing .* secret)\b",
    r"\b(?:source integrity|source coverage|data mismatch|count mismatch)\b",
)

def matches(logs: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, logs, flags=re.I | re.M) for p in patterns)

def aware(text):
    try:
        dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        return dt if dt.tzinfo else None
    except (TypeError, ValueError):
        return None

def decide(run: dict, jobs: list, logs: str, main_sha: str,
           manifest: dict | None, now: datetime) -> tuple[str, str]:
    """One first-attempt repair only, with proof of a failure on current main."""
    name = str(run.get("name", ""))
    if name in COLLECTOR_BLOCKLIST:
        return "skip", "Never rerun source collectors or END email automatically: duplicate evidence or mail risk."
    if name not in RERUN_ALLOWLIST:
        return "skip", "Not on the approved repair workflow allowlist."
    if (run.get("status") != "completed" or run.get("conclusion") != "failure"
            or run.get("run_attempt") != 1):
        return "skip", "Only completed failures on their first attempt are eligible."
    if (run.get("head_branch") != "main"
            or run.get("event") not in {"push", "schedule", "workflow_dispatch"}
            or not main_sha or run.get("head_sha") != main_sha):
        return "skip", "Non-main, unsafe trigger or superseded commit."
    if not logs.strip():
        return "skip", "No verified failure logs; do not retry blindly."
    if not any(j.get("conclusion") == "failure" for j in jobs):
        return "skip", "No failed job on the last attempt."

    if name in {"PRE PHASE 3 Live Acceptance", "PIPELINE Early Clinical Live Acceptance",
                "Live Streamlit Cloud Browser Audit"}:
        expired = (re.search(r"Source integration failed", logs, re.I)
                   and re.search(r"(?:Error type:\s*ValueError|past its Pacific-day cutoff)", logs, re.I))
        generated = aware((manifest or {}).get("generated_at_utc"))
        if expired and (generated is None or
                        generated.astimezone(PACIFIC).date() < now.astimezone(PACIFIC).date()):
            return "refresh_pre3", "Rebuild expired PRE3 cache with existing validated publisher."
    if matches(logs, PERMANENT):
        return "skip", "Deterministic code, test, auth or source-integrity failure: manual review required."
    if matches(logs, TRANSIENT):
        return "rerun", "Explicit network/infrastructure failure; re-run only failed jobs once."
    return "skip", "Unclassified failure: no unverified automatic code changes."

def main():
    p = argparse.ArgumentParser()
    for name in ("run-json", "jobs-json", "logs", "manifest"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--main-sha", required=True)
    p.add_argument("--github-output", required=True)
    a = p.parse_args()
    run = json.loads(a.run_json.read_text(encoding="utf-8"))
    jobs = json.loads(a.jobs_json.read_text(encoding="utf-8")).get("jobs", [])
    logs = a.logs.read_text(encoding="utf-8", errors="replace") if a.logs.is_file() else ""
    manifest = json.loads(a.manifest.read_text(encoding="utf-8")) if a.manifest.is_file() else None
    action, reason = decide(run, jobs, logs, a.main_sha, manifest,
                            datetime.now(timezone.utc))
    with open(a.github_output, "a", encoding="utf-8") as out:
        out.write("action=" + action + "\nreason=" + reason.replace("\n", " ") + "\n")
    print(json.dumps({"action": action, "reason": reason,
                      "run_id": run.get("id"), "attempt": run.get("run_attempt")}))

if __name__ == "__main__":
    main()

