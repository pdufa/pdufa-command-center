"""Select a Pacific-time surveillance run and verify the required steps ran.

GitHub supports IANA timezones on cron schedules. Do not compare runner wall
clock times to the scheduled minute: hosted runners may start late.
"""
import json
from datetime import datetime, timezone

SCHEDULES = {
    "15 5 * * *": "daily",
    "0 4 * * 0": "weekly",
    "30 4 1 * *": "monthly",
}
MODES = set(SCHEDULES.values()) | {"full"}
REQUIRED_STEPS = {
    "daily": ("discovery_daily", "recheck_daily", "refresh_fda", "validate"),
    "weekly": ("discovery_daily", "recheck_weekly", "refresh_fda", "validate"),
    "monthly": ("discovery_monthly", "recheck_monthly", "refresh_fda", "validate"),
    "full": (
        "discovery_daily", "discovery_monthly", "recheck_daily",
        "recheck_weekly", "recheck_monthly", "refresh_fda", "validate",
    ),
}


def mode_for_schedule(cron):
    """Map the scheduled event itself, independent of its delayed start time."""
    if cron not in SCHEDULES:
        raise ValueError(f"Unknown surveillance cron: {cron!r}")
    return SCHEDULES[cron]


def mode_for_trigger(event_name, cron="", manual_mode=""):
    if event_name == "schedule":
        return mode_for_schedule(cron)
    if event_name == "workflow_dispatch" and manual_mode in MODES:
        return manual_mode
    raise ValueError(f"Unexpected surveillance event/mode: {event_name!r}/{manual_mode!r}")


def verify_run_steps(mode, steps):
    """Reject success if a mandatory collector or validation was skipped."""
    if mode not in REQUIRED_STEPS:
        raise ValueError(f"Unknown surveillance mode: {mode!r}")
    missed = [
        name for name in REQUIRED_STEPS[mode]
        if steps.get(name, {}).get("outcome") != "success"
    ]
    if missed:
        raise ValueError("Required surveillance steps not successful: " + ", ".join(missed))
    return {
        "status": "COMPLETE",
        "mode": mode,
        "required_steps": list(REQUIRED_STEPS[mode]),
        "step_outcomes": {
            name: str(info.get("outcome", "unknown"))
            for name, info in steps.items() if isinstance(info, dict)
        },
    }


def make_run_record(mode, steps, event_name, cron, run_id, finished_at=None):
    record = verify_run_steps(mode, steps)
    record.update({
        "event": event_name,
        "schedule": cron,
        "timezone": "America/Los_Angeles",
        "github_run_id": str(run_id),
        "finished_at_utc": finished_at or datetime.now(timezone.utc).isoformat(),
        "note": "Completed workflow steps do not prove that external FDA/SEC sources were reachable.",
    })
    return record


if __name__ == "__main__":
    import argparse
    import os
    from pathlib import Path

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--resolve", action="store_true")
    group.add_argument("--record", action="store_true")
    options = parser.parse_args()
    event = os.environ.get("GH_EVENT_NAME", "")
    schedule = os.environ.get("GH_SCHEDULE", "")

    if options.resolve:
        selected = mode_for_trigger(event, schedule, os.environ.get("MANUAL_MODE", ""))
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("run=yes\nmode=" + selected + "\n")
        print(f"Surveillance mode={selected} event={event} cron={schedule!r}")
    else:
        selected = os.environ["SURVEILLANCE_MODE"]
        outcomes = json.loads(os.environ["SURVEILLANCE_STEPS"])
        record = make_run_record(
            selected, outcomes, event, schedule, os.environ.get("GITHUB_RUN_ID", "")
        )
        Path("data/surveillance_run_state.json").write_text(
            json.dumps(record, indent=2) + "\n", encoding="utf-8"
        )
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_file:
            with open(summary_file, "a", encoding="utf-8") as summary:
                summary.write(
                    f"### Verified surveillance: {selected}\n\n"
                    + "Executed steps: " + ", ".join(record["required_steps"]) + "\n\n"
                    + "Source coverage must be audited separately.\n"
                )
        print("Verified required steps:", ", ".join(record["required_steps"]))
