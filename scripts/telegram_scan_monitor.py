#!/usr/bin/env python3
"""24/7 GitHub Actions scan monitor for opt-in Telegram alerts.

Polls actual scan workflow runs, never assumes a cron dispatch means a scan ran.
State is stored in a GitHub Actions cache, not in the clinical repository.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

from telegram_scan_alert import main as notify

REPO = "pdufa/pdufa-command-center"
API = "https://api.github.com/repos/" + REPO + "/actions/runs?per_page=100&page="
SCAN_PREFIXES = (
    "pdufa-individual-", "pdufa-nightly-", "pdufa-filings-", "pdufa-pipeline-",
    "pdufa-scan-", "pdufa-adhoc-", "pdufa-sec-", "pdufa-onetime-",
    "pdufa-one-time-", "pdufa-overnight-", "main-phase3-",
    "main-130-", "main-sva-", "raas-", "phase3-", "nightly-registry-",
    "fda-source-", "hop-fda-", "hop-drugsfda-",
)
# Existing workflows send instantaneous start/end alerts themselves.
DIRECT_ALERTS = {"pdufa-overnight-sequential.yml", "raas-fda-decision-accuracy.yml"}
EVENTS = {"schedule", "workflow_dispatch", "repository_dispatch", "workflow_run"}
MAX_PAGES = 5
MAX_LOOKBACK_HOURS = 48


def is_active_scan(run):
    if not isinstance(run, dict) or run.get("event") not in EVENTS:
        return False
    path = str(run.get("path") or "").rsplit("/", 1)[-1].lower()
    title = str(run.get("name") or "") + " " + str(run.get("display_title") or "")
    if path in DIRECT_ALERTS or path.startswith("pdufa-telegram-"):
        return False
    # Retired GEM / GEM JR must never be reintroduced through monitoring.
    if "gem" in path or re.search(r"\bGEM\s*(?:JR)?\b", title, re.I):
        return False
    if not path.startswith(SCAN_PREFIXES):
        return False
    if any(x in path for x in ("-tests", "-test.", "-checks", "-smoke", "-ci-", "-backup")):
        return False
    return True


def event_key(run):
    return str(run["id"]) + ":" + str(run.get("run_attempt") or 1)


def changes(runs, known, initializing=False):
    """Returns a list of (event, run), and a new durable state."""
    updated = dict(known)
    alerts = []
    for run in reversed(runs):
        if not is_active_scan(run):
            continue
        key = event_key(run)
        existing = dict(updated.get(key) or {})
        status = str(run.get("status") or "")
        conclusion = str(run.get("conclusion") or "")
        if not initializing:
            if status == "in_progress" and not existing.get("started"):
                alerts.append(("scan-start", run))
                existing["started"] = True
            if status == "completed" and not existing.get("ended"):
                alerts.append(("scan-end", run))
                existing["ended"] = True
                existing["started"] = True
        else:
            # First run must seed rather than flood the owner with old alerts.
            existing["started"] = status in {"in_progress", "completed"}
            existing["ended"] = status == "completed"
        existing["conclusion"] = conclusion
        existing["workflow"] = run.get("path")
        existing["updated_at"] = run.get("updated_at")
        updated[key] = existing
    # Keep cache bounded (roughly last 1,500 attempts).
    if len(updated) > 1500:
        updated = dict(list(updated.items())[-1500:])
    return alerts, updated


def load_runs():
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Missing GitHub token")
    oldest = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=MAX_LOOKBACK_HOURS)
    results = []
    for page in range(1, MAX_PAGES + 1):
        req = urllib.request.Request(API + str(page), headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "pdufa-telegram-scan-monitor",
            "Authorization": "Bearer " + token,
        })
        with urllib.request.urlopen(req, timeout=15) as response:
            payload = json.load(response)
        batch = payload.get("workflow_runs")
        if not isinstance(batch, list):
            raise RuntimeError("Invalid GitHub workflow data")
        results.extend(batch)
        if len(batch) < 100:
            break
        try:
            last_created = dt.datetime.fromisoformat(batch[-1]["created_at"].replace("Z", "+00:00"))
            if last_created < oldest:
                break
        except (ValueError, TypeError, KeyError):
            raise RuntimeError("Unknown GitHub workflow timestamps")
    # Only recent runs, but a scan started earlier may still be active.
    return [r for r in results if isinstance(r, dict) and
            (r.get("status") in ("queued", "in_progress", "waiting", "pending") or
             dt.datetime.fromisoformat(str(r.get("created_at") or "1970-01-01T00:00:00Z")
                                        .replace("Z", "+00:00")) >= oldest)]


def run(state_file):
    state_path = Path(state_file)
    initialized = state_path.exists()
    try:
        state = json.loads(state_path.read_text()) if initialized else {}
        if not isinstance(state, dict):
            raise ValueError("Invalid state")
    except (OSError, ValueError) as e:
        raise RuntimeError("Monitor cache could not be read safely") from e
    fetched = load_runs()
    alerts, updated = changes(fetched, state, not initialized)
    success_count = 0
    for kind, item in alerts:
        name = str(item.get("name") or item.get("path") or "Unknown scan")[:140]
        state_name = str(item.get("conclusion") or item.get("status") or "UNKNOWN")
        run_url = str(item.get("html_url") or "")
        info = name + " | " + ("Run started." if kind == "scan-start"
                             else "Run finished: " + state_name + ". Check source completeness separately.")
        result = notify(["--event", kind,
                         "--status", state_name if kind == "scan-end" else "in_progress",
                         "--details", info, "--url", run_url])
        if result != 0:
            # Retry this event next polling tick.
            key = event_key(item)
            if key in updated:
                updated[key]["started" if kind == "scan-start" else "ended"] = False
        else:
            success_count += 1
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(updated, sort_keys=True, indent=2) + "\n")
    print(f"Monitor complete: {len(fetched)} recent workflow runs; "
          f"{len(alerts)} alerts attempted, {success_count} delivered to Telegram API; "
          f"{'initialized' if not initialized else 'restored'} state.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run(os.environ.get("PDUFA_TELEGRAM_MONITOR_STATE", ".cache/pdufa-telegram-monitor-state.json")))
    except Exception:
        print("::error::Telegram scan monitor could not validate GitHub run data/state; no success assumed.")
        sys.exit(1)
