"""Single timing source for the user's post-Phase-3 / second-financing GEM strategy.

The -3 cutoff is a planned exit deadline, NOT evidence FDA action waits until
then. "New entry" requires four or more calendar days to the target date.
No brokerage calendar is assumed: move weekend deadlines back to Friday;
actual exchange holidays, halts, and early FDA decisions need separate review.
"""
from __future__ import annotations

from datetime import date, timedelta

EXIT_BUFFER_DAYS = 3
MIN_NEW_ENTRY_DAYS = EXIT_BUFFER_DAYS + 1


def calendar_exit_target(pdufa: date) -> date:
    if not isinstance(pdufa, date):
        raise ValueError("A confirmed PDUFA date is required")
    return pdufa - timedelta(days=EXIT_BUFFER_DAYS)


def latest_weekday_exit(pdufa: date) -> date:
    """Conservative weekend adjustment; not an exchange holiday calendar."""
    target = calendar_exit_target(pdufa)
    return target - timedelta(days=max(0, target.weekday() - 4))


def is_new_entry_window(days_to_pdufa: int | None) -> bool:
    return type(days_to_pdufa) is int and days_to_pdufa >= MIN_NEW_ENTRY_DAYS
