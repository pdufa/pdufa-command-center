"""DST-aware, once-per-night admission to the complete sequential scan run."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
RUN_TITLE = "ALL + GEM — PDUFA overnight"
WORKFLOW = ".github/workflows/pdufa-overnight-sequential.yml"
RECOVERY_CRONS = {f"{minute} {hour} * * *" for hour in (7, 8, 9) for minute in (5, 35)}
# One spaced-out cron expression provides frequent recovery opportunities.
# GitHub schedule execution is best-effort; the clock gate below ensures
# pre-10 PM Pacific events cannot start a scan and allows safe late recovery.
SWEEP_CRON = "3-53/10 5-10 * * *"
ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}


def decision(event, cron, runs, *, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = now.astimezone(PACIFIC)
    # Scheduled after-midnight recovery belongs to the preceding night.
    # A manual dispatch should reflect the actual requested Pacific date.
    night = local if (event == "workflow_dispatch" or local.hour >= 22) else local - timedelta(days=1)
    start = night.replace(hour=22, minute=0, second=0, microsecond=0)
    weekly_full = start.weekday() == 6  # Sunday night in Los Angeles, including after-midnight recovery
    result = {"run": False, "night_date_pacific": start.date().isoformat(),
              "scan_mode": "FULL" if weekly_full else "DELTA",
              "gem_action": "RESCAN_ALL" if weekly_full else "REVERIFY_PARTIAL",
              "reason": ""}
    in_window = local.hour >= 22 or local.hour < 3
    primary_hour = start.astimezone(timezone.utc).hour
    primary = {f"{minute} {primary_hour} * * *" for minute in (0, 15, 30)}
    allowed = (event == "workflow_dispatch" or
               event == "push" and local.hour == 22 or
               event == "schedule" and in_window and
               (cron in primary or (local.hour < 3 and cron in RECOVERY_CRONS) or
                cron == SWEEP_CRON))
    if not allowed:
        result["reason"] = "Outside the matching 10 PM–2:59 AM Pacific start/recovery window"
        return result
    for run in runs:
        if (run.get("path", "").split("@", 1)[0] != WORKFLOW or
                run.get("head_branch") != "main" or
                run.get("event") != "workflow_dispatch" or
                run.get("display_title") != RUN_TITLE):
            continue
        try:
            created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
            if created.tzinfo is None:
                raise ValueError("Timestamp has no timezone")
        except (KeyError, TypeError, ValueError):
            # Unknown current state cannot safely authorize a duplicate.
            result["reason"] = "Existing full-run timestamp is invalid; inspect before restarting"
            return result
        if run.get("status") in ACTIVE or start.astimezone(timezone.utc) <= created <= now:
            result["reason"] = f"Full nightly chain already recorded or active (run {run.get('id')})"
            return result
    result.update(run=True, reason=("Sunday FULL reconciliation" if weekly_full else
                                     "Weekday DELTA changes/new-trial check") + "; start awaited chain including GEM")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    parser.add_argument("--cron", default="")
    parser.add_argument("--runs-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.runs_json.read_text(encoding="utf-8"))
    runs = payload.get("workflow_runs")
    if not isinstance(runs, list):
        raise SystemExit("Cannot verify existing overnight runs; no dispatch")
    result = decision(args.event, args.cron, runs)
    with args.output.open("a", encoding="utf-8") as handle:
        for key, value in result.items():
            handle.write(f"{key}={str(value).lower() if isinstance(value, bool) else value}\n")
    print(result["reason"])


if __name__ == "__main__":
    main()
