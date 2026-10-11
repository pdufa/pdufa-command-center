"""Fast, fail-closed Streamlit reader for the GitHub-generated Step 7 display feed.

The feed's existing generation step performs provenance checks and scores all
exact trial rows once. Streamlit should display that dated result, not repeat
the expensive full-universe join on every browser navigation.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from pre_phase3_priority import POINT_COLUMNS, RUBRIC_VERSION
from step7_live import read_csv, read_json

NCT = re.compile(r"NCT\d{8}\Z")
PACIFIC = ZoneInfo("America/Los_Angeles")
INT_FIELDS = {
    "Review priority /100", "Review priority rank",
    "Phase 2 PRIMARY evidence count", "Design inputs present /6",
    *POINT_COLUMNS,
}
OPTIONAL_INT_FIELDS = {"Review priority rank"}
OPTIONAL_SCORES = {
    "Preliminary clinical score /100",
    "Pre-readout research score /100",
}
FLOAT_FIELDS = {"Market cap USD"}


def _aware(raw):
    try:
        when = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
        return when.astimezone(timezone.utc) if when.tzinfo else None
    except (ValueError, TypeError, OverflowError):
        return None


def _number(raw, numeric_type, optional=False):
    value = str(raw or "").strip()
    if not value and optional:
        return None
    if not value:
        raise ValueError("Required numeric field missing from Step 7 feed")
    number = numeric_type(value)
    if numeric_type is int and str(number) != value:
        raise ValueError("Expected integer in Step 7 feed")
    return number


def load_current_snapshot(data_root, now):
    """Return (trials, financing, manifest) if fully validated for Pacific today.

    Return None if a feed is absent, stale or internally inconsistent. Caller
    must show a refresh-required error rather than resurrect old clinical scores.
    No external HTTP request or new scoring is made inside this reader.
    """
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    root = Path(data_root)
    state = root / "step7_live_status.json"
    trial_file = root / "step7_pre_phase3_feed.csv"
    finance_file = root / "step7_financing_review.csv"
    if not (state.is_file() and trial_file.is_file() and finance_file.is_file()):
        return None
    manifest = read_json(state)
    cutoff = _aware(manifest.get("generated_at_utc"))
    if (cutoff is None or cutoff > now.astimezone(timezone.utc)
            or cutoff.astimezone(PACIFIC).date() != now.astimezone(PACIFIC).date()
            or manifest.get("review_priority_rubric") != RUBRIC_VERSION):
        return None

    rows = read_csv(trial_file)
    finance = read_csv(finance_file)
    if (not rows or len(rows) != manifest.get("trial_rows")
            or len(rows) != manifest.get("review_priority_rows")
            or len(finance) != manifest.get("financing_events")):
        return None
    seen = set()
    active_ranks = []
    excluded = 0
    try:
        for row in rows:
            ticker, nct = row.get("Ticker", ""), row.get("NCT ID", "")
            identity = (ticker, nct)
            if (not ticker or not NCT.fullmatch(nct) or identity in seen
                    or row.get("NCT source") != f"https://clinicaltrials.gov/study/{nct}"
                    or row.get("Review priority rubric") != RUBRIC_VERSION
                    or not _aware(row.get("Review priority as of"))):
                return None
            seen.add(identity)
            for field in INT_FIELDS:
                row[field] = _number(row.get(field), int, field in OPTIONAL_INT_FIELDS)
            for field in OPTIONAL_SCORES | FLOAT_FIELDS:
                row[field] = _number(row.get(field), float, True)
            priority = row["Review priority /100"]
            rank = row["Review priority rank"]
            if not 0 <= priority <= 100 or priority != sum(row[c] for c in POINT_COLUMNS):
                return None
            if row.get("Review priority status", "").startswith("EXCLUDED"):
                excluded += 1
                if priority != 0 or rank is not None:
                    return None
            else:
                if rank is None:
                    return None
                active_ranks.append(rank)
        if (sorted(active_ranks) != list(range(1, len(active_ranks) + 1))
                or len(active_ranks) != manifest.get("review_priority_ranked")
                or excluded != manifest.get("review_priority_excluded")):
            return None
    except (ValueError, TypeError, OverflowError, KeyError):
        return None
    return rows, finance, manifest
