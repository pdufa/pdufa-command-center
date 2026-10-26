#!/usr/bin/env python3
"""Select one nightly 8 PM America/Los_Angeles scan across PST/PDT.

GitHub cron is UTC, so both 03:00 and 04:00 UTC are configured.
Only the entry corresponding to 20:00 Pacific local time runs the
costly read-only 741-NCT / 130-issuer source workflow. The other entry
intentionally skips. Workflow dispatch and pull requests always run.
GitHub may delay scheduled jobs; no exactly-on-time execution guarantee.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
SUMMER_CRON = "0 3 * * *"
WINTER_CRON = "0 4 * * *"
SCHEDULES = (SUMMER_CRON, WINTER_CRON)
EVENTS = ("workflow_dispatch", "pull_request", "schedule")


def decide(event_name: str, event_schedule: str, now: datetime) -> dict:
    """Pure predicate with explicit local-date and daylight-saving metadata."""
    if event_name not in EVENTS:
        raise ValueError("Unexpected GitHub event; refusing to scan")
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("An offset-aware observation time is mandatory")
    local = now.astimezone(PACIFIC)
    desired = SUMMER_CRON if local.dst() else WINTER_CRON
    if event_name == "schedule":
        if event_schedule not in SCHEDULES:
            raise ValueError("Unexpected schedule expression; refusing to scan")
        proceed = event_schedule == desired
        reason = ("SCHEDULED_PACIFIC_8PM" if proceed
                  else "OFF_SEASON_DST_ALTERNATE_SKIPPED")
    else:
        proceed = True
        reason = "AUTHORIZED_ON_DEMAND_OR_PR_SOURCE_CHECK"
    return {
        "proceed": proceed,
        "reason": reason,
        "pacific_date": local.date().isoformat(),
        "local_zone": local.tzname(),
        "expected_cron": desired,
        "actual_schedule": event_schedule if event_name == "schedule" else None,
        "disclaimer": "Scheduled time is nominal: GitHub Actions may start late.",
    }


def write_outcome(outcome: dict, github_output: Path, github_summary: Path | None) -> None:
    if not isinstance(outcome.get("proceed"), bool):
        raise ValueError("Invalid gate outcome")
    github_output.parent.mkdir(parents=True, exist_ok=True)
    with github_output.open("a", encoding="utf-8") as handle:
        handle.write("proceed=" + ("true" if outcome["proceed"] else "false") + "\n")
        handle.write("pacific_date=" + outcome["pacific_date"] + "\n")
    if github_summary:
        with github_summary.open("a", encoding="utf-8") as handle:
            handle.write("## MAIN Phase 3 nightly schedule gate\n\n")
            handle.write("| Field | Value |\n|:--|:--|\n")
            handle.write("| Nominal local scan | 8:00 PM America/Los_Angeles |\n")
            handle.write(f"| Local research date | {outcome['pacific_date']} ({outcome['local_zone']}) |\n")
            handle.write(f"| Gate decision | {outcome['reason']} |\n")
            handle.write(f"| Full evidence run | {'ENABLED' if outcome['proceed'] else 'SKIPPED — DST alternate'} |\n")
            handle.write("\nThis source research does not update Pipeline, GEM JR, GEM, or FS/FA presets. "
                         "The dashboard historical scorecard remains a separately pinned archive.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-schedule", default="")
    parser.add_argument("--github-output", required=True, type=Path)
    parser.add_argument("--github-summary", type=Path)
    args = parser.parse_args()
    result = decide(args.event_name, args.event_schedule, datetime.now(timezone.utc))
    write_outcome(result, args.github_output, args.github_summary)
    print(
        f"MAIN nightly schedule gate: {result['reason']}, "
        f"proceed={result['proceed']}, "
        f"Pacific date={result['pacific_date']} ({result['local_zone']}); "
        "GitHub runner timing is best-effort"
    )


if __name__ == "__main__":
    main()
