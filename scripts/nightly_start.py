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
ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}


def decision(event, cron, runs, *, now=None):
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = now.astimezone(PACIFIC)
    night = local if local.hour >= 21 else local - timedelta(days=1)
    start = night.replace(hour=21, minute=0, second=0, microsecond=0)
    result = {"run": False, "night_date_pacific": start.date().isoformat(), "reason": ""}
    in_window = local.hour >= 21 or local.hour < 3
    primary_hour = start.astimezone(timezone.utc).hour
    primary = {f"{minute} {primary_hour} * * *" for minute in (0, 15, 30)}
    allowed = (event == "workflow_dispatch" or
               event == "push" and local.hour == 21 or
               event == "schedule" and in_window and
               (cron in primary or local.hour < 3 and cron in RECOVERY_CRONS))
    if not allowed:
        result["reason"] = "Outside the matching 9 PM–2:59 AM Pacific start/recovery window"
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
    result.update(run=True, reason="No full chain for this Pacific night; start ALL scans including GEM")
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
