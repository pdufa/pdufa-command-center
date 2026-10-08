"""Daily PDUFA countdown segmentation and within-segment color gradients."""
import pandas as pd

SEGMENTS = ("0–30 DAYS", "31–60 DAYS", "61–90 DAYS", "90+ DAYS")

def segment(days):
    if pd.isna(days):
        return "DATE UNKNOWN"
    days = int(days)
    if days < 0:
        return "PAST DUE"
    if days <= 30:
        return SEGMENTS[0]
    if days <= 60:
        return SEGMENTS[1]
    if days <= 90:
        return SEGMENTS[2]
    return SEGMENTS[3]

def _blend(start, end, fraction):
    fraction = max(0.0, min(1.0, fraction))
    rgb = tuple(round(a + (b - a) * fraction) for a, b in zip(start, end))
    return "#%02x%02x%02x" % rgb

def date_color(days):
    """Nearer dates are darker within their own segment; text remains black."""
    if pd.isna(days):
        return ""
    days = int(days)
    if days < 0:
        return "background-color:#e5e7eb;color:#111111"
    if days <= 30:
        lo, hi, dark, light = 0, 30, (239, 108, 108), (255, 224, 224)
    elif days <= 60:
        lo, hi, dark, light = 31, 60, (249, 157, 72), (255, 234, 199)
    elif days <= 90:
        lo, hi, dark, light = 61, 90, (241, 205, 63), (255, 249, 200)
    else:
        lo, hi, dark, light = 91, 180, (113, 196, 126), (221, 247, 222)
    return "background-color:" + _blend(dark, light, (days - lo) / (hi - lo)) + ";color:#111111"

def add_countdown(frame, date_col="PDUFA Date", today=None):
    out = frame.copy()
    today = pd.Timestamp(today).normalize() if today is not None else pd.Timestamp.now(tz="America/Los_Angeles").tz_localize(None).normalize()
    dates = pd.to_datetime(out[date_col], errors="coerce", utc=True).dt.tz_localize(None).dt.normalize()
    out["DAYS TO PDUFA"] = (dates - today).dt.days.astype("Int64")
    out["PDUFA Horizon"] = out["DAYS TO PDUFA"].map(segment)
    return out
