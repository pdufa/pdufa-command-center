"""Shared PDUFA countdown colors and range labels for every PDUFA chart.

Strict boundaries: >90 dark green, 60-90 green, 30-59 orange,
0-29 red. Past due and unknown never receive active-window colors.
"""
import pandas as pd

SEGMENTS = ("29–0 DAYS", "59–30 DAYS", "90–60 DAYS", "90+ DAYS")
# Labels match the user-facing second line below DAYS TO PDUFA.
COUNTDOWN_BANDS = (
    ("+90", "dark-green", "#166534", "#ffffff"),
    ("90–60", "green", "#86efac", "#111111"),
    ("59–30", "orange", "#fb923c", "#111111"),
    ("29–0", "red", "#f87171", "#111111"),
)
COUNTDOWN_HEADER_SUBLINE = "🟩 +90   🟢 90–60   🟠 59–30   🔴 29–0"


def _days(value):
    try:
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.isna(parsed):
            return None
        return int(parsed)
    except (ValueError, TypeError, OverflowError):
        return None


def band_index(days):
    """Return a visual band index, or None for past-due/unverified dates."""
    days = _days(days)
    if days is None or days < 0:
        return None
    if days > 90:
        return 0
    if days >= 60:
        return 1
    if days >= 30:
        return 2
    return 3


def segment(days):
    value = _days(days)
    if value is None:
        return "DATE UNKNOWN"
    if value < 0:
        return "PAST DUE"
    index = band_index(value)
    return SEGMENTS[(3, 2, 1, 0)[index]]


def date_color(days):
    """CSS for a countdown cell using the four exact user-selected ranges."""
    value = _days(days)
    if value is None:
        return ""
    if value < 0:
        return "background-color:#e5e7eb;color:#111111"
    _, _, background, foreground = COUNTDOWN_BANDS[band_index(value)]
    return f"background-color:{background};color:{foreground};font-weight:700"


def add_countdown(frame, date_col="PDUFA Date", today=None):
    out = frame.copy()
    today = pd.Timestamp(today).normalize() if today is not None else pd.Timestamp.now(tz="America/Los_Angeles").tz_localize(None).normalize()
    dates = pd.to_datetime(out[date_col], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    out["DAYS TO PDUFA"] = (dates - today).dt.days.astype("Int64")
    out["PDUFA Horizon"] = out["DAYS TO PDUFA"].map(segment)
    return out
