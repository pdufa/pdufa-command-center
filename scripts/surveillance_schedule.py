"""Resolve GitHub cron events without assuming jobs start on time.

The duplicated UTC cron entries allow local Pacific daylight-saving time;
only the entry matching the intended local wall clock is allowed to process.
"""
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")
# cron expression -> (run mode, expected Pacific hour, expected Pacific minute)
SCHEDULES = {
    "15 12 * * *": ("daily", 5, 15),
    "15 13 * * *": ("daily", 5, 15),
    "0 11 * * 0": ("weekly", 4, 0),
    "0 12 * * 0": ("weekly", 4, 0),
    "30 11 1 * *": ("monthly", 4, 30),
    "30 12 1 * *": ("monthly", 4, 30),
}


def mode_for_schedule(cron, now_utc=None):
    """Return daily/weekly/monthly or skip for a scheduled UTC cron event.

    Evaluate the intended scheduled instant, not the runner's actual Pacific
    clock minute. GitHub-hosted runners can start many minutes or hours late.
    """
    if cron not in SCHEDULES:
        return "skip"
    mode, local_hour, local_minute = SCHEDULES[cron]
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    now = now.astimezone(timezone.utc)
    minute, hour = (int(piece) for piece in cron.split()[:2])
    intended_utc = datetime.combine(
        now.date(), time(hour=hour, minute=minute, tzinfo=timezone.utc)
    )
    if intended_utc > now:
        intended_utc -= timedelta(days=1)
    local_date = intended_utc.astimezone(PACIFIC).date()
    if mode == "weekly" and local_date.weekday() != 6:
        return "skip"
    if mode == "monthly" and local_date.day != 1:
        return "skip"
    target_utc = datetime.combine(
        local_date, time(hour=local_hour, minute=local_minute, tzinfo=PACIFIC)
    ).astimezone(timezone.utc)
    return mode if intended_utc == target_utc else "skip"
