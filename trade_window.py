"""Single research cutoff for the user-defined post-Phase-3 trading plan.

After an independently verified second post-Phase-3 financing closure,
evaluate possible entries only while more than three CALENDAR days remain
until the verified PDUFA target. Exit monitoring flags PDUFA minus three;
these are research controls, not trade orders or return forecasts.
"""
EXIT_DAYS_BEFORE_PDUFA = 3
LAST_ENTRY_MIN_DAYS = EXIT_DAYS_BEFORE_PDUFA + 1
