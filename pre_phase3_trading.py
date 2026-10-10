"""Visible prospective Phase 3 trading-*research* queue.

The completion dates in the trial registry are NOT confirmed corporate
topline-release dates. No stock is declared entry-ready by this screen.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
import pandas as pd

SHORTLIST_COLUMNS = [
    "Ticker", "Drug", "Indication", "NCT ID", "Registry Primary Completion",
    "Completion Date Precision", "Primary Completion Type",
    "Market Cap", "Program Identity", "Phase 2 p Evidence",
    "Issuer Readout Date", "Financing / Dilution", "Price / Liquidity",
    "Trading Entry Gate", "Registry Source",
]

def _completion_bounds(value):
    """Return earliest/latest possible completion dates without faking day precision."""
    text = str(value or "").strip()
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            day = date.fromisoformat(text)
            return day, day, "DAY"
        if re.fullmatch(r"\d{4}-\d{2}", text):
            year, month = map(int, text.split("-"))
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1]), "MONTH ONLY"
    except ValueError:
        pass
    return None, None, "NOT VERIFIED"

def trading_research_queue(candidates, as_of, lookahead_days=180):
    """Screen possible future registry completion windows, never issuer readouts.

    This is a discovery shortlist. No publication, pre-readout or entry
    qualification is inferred from active registry status.
    """
    if lookahead_days not in (90, 180, 365):
        raise ValueError("lookahead_days must be 90, 180 or 365")
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    if candidates is None or candidates.empty:
        return pd.DataFrame(columns=SHORTLIST_COLUMNS)

    last_day = as_of + timedelta(days=lookahead_days)
    records = []
    for _, item in candidates.iterrows():
        first, last, precision = _completion_bounds(item.get("Primary Completion", ""))
        if first is None or last < as_of or first > last_day:
            continue
        row = {
            "Ticker": str(item.get("Ticker", "")).upper().strip(),
            "Drug": str(item.get("Drug", "")).strip(),
            "Indication": str(item.get("Indication", "")).strip(),
            "NCT ID": str(item.get("NCT ID", "")).strip(),
            "Registry Primary Completion": str(item.get("Primary Completion", "")).strip(),
            "Completion Date Precision": precision,
            "Primary Completion Type": str(item.get("Primary Completion Type", "")).strip(),
            "Market Cap": item.get("Market Cap", pd.NA),
            "Program Identity": str(item.get("Program Identity", "REVIEW")).strip(),
            "Phase 2 p Evidence": str(item.get("Phase 2 p Evidence", "NOT VERIFIED")).strip() or "NOT VERIFIED",
            "Issuer Readout Date": "NOT VERIFIED",
            "Financing / Dilution": "NOT CHECKED",
            "Price / Liquidity": "NOT CHECKED",
            "Trading Entry Gate": "REVIEW — NOT ENTRY-READY",
            "Registry Source": str(item.get("Source", "")).strip(),
            "_sort_date": first,
        }
        if row["Ticker"] and re.fullmatch(r"NCT\d{8}", row["NCT ID"]):
            records.append(row)
    if not records:
        return pd.DataFrame(columns=SHORTLIST_COLUMNS)
    return (pd.DataFrame(records)
            .sort_values(["_sort_date", "Ticker", "NCT ID"], kind="stable")
            .drop_duplicates(["Ticker", "NCT ID"], keep="first")
            [SHORTLIST_COLUMNS].reset_index(drop=True))
