"""Visible prospective Phase 3 trading-*research* queue.

The completion dates in the trial registry are NOT confirmed corporate
topline-release dates. No stock is declared entry-ready by this screen.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
import pandas as pd

# Clinical scores require a completely sourced pre-readout assessment. A
# metadata-coverage percentage is never substituted for an unverified score.
SHORTLIST_COLUMNS = [
    "Ticker", "PRE PHASE 3 Score /100", "Phase 2 Clinical /25",
    "Phase 3 Pre-Readout /75", "PRE PHASE 3 Score Status",
    "Documented Inputs %", "Basic Design Safeguards /5",
    "Drug", "Indication", "NCT ID", "Registry Primary Completion",
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
        # Combine only if the separately reviewed Phase 2 + Phase 3 source
        # checks passed. A partial/protocol metadata score is NOT a substitute.
        combined_status = str(item.get("Combined Score Status", "")).strip()
        verified = combined_status == "COMBINED RESEARCH SCORE — NOT A PROBABILITY"
        total = pd.to_numeric(item.get("Combined Pre-Readout Score /100", pd.NA), errors="coerce")
        phase2 = pd.to_numeric(item.get("Phase 2 Clinical Score /25", pd.NA), errors="coerce")
        phase3 = pd.to_numeric(item.get("Phase 3 Pre-Readout Score /75", pd.NA), errors="coerce")
        score_valid = (verified and pd.notna(total) and pd.notna(phase2)
                       and pd.notna(phase3) and 0 <= total <= 100
                       and 0 <= phase2 <= 25 and 0 <= phase3 <= 75
                       and abs(float(total) - float(phase2) - float(phase3)) < 0.001)
        documented = pd.to_numeric(item.get("Input Coverage %", pd.NA), errors="coerce")
        if pd.isna(documented) or not 0 <= documented <= 100:
            documented = pd.NA
        safeguards = pd.to_numeric(item.get("Basic Design Safeguards /5", pd.NA), errors="coerce")
        if pd.isna(safeguards) or not 0 <= safeguards <= 5:
            safeguards = pd.NA
        row = {
            "Ticker": str(item.get("Ticker", "")).upper().strip(),
            "PRE PHASE 3 Score /100": float(total) if score_valid else pd.NA,
            "Phase 2 Clinical /25": float(phase2) if score_valid else pd.NA,
            "Phase 3 Pre-Readout /75": float(phase3) if score_valid else pd.NA,
            "PRE PHASE 3 Score Status": (
                combined_status if score_valid
                else "NOT SCORED — SOURCE-VERIFIED CLINICAL REVIEW REQUIRED"
            ),
            "Documented Inputs %": float(documented) if pd.notna(documented) else pd.NA,
            "Basic Design Safeguards /5": float(safeguards) if pd.notna(safeguards) else pd.NA,
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
    out = (pd.DataFrame(records)
           .sort_values(["_sort_date", "Ticker", "NCT ID"], kind="stable")
           .drop_duplicates(["Ticker", "NCT ID"], keep="first")
           [SHORTLIST_COLUMNS].reset_index(drop=True))
    for column in ("PRE PHASE 3 Score /100", "Phase 2 Clinical /25",
                   "Phase 3 Pre-Readout /75", "Documented Inputs %",
                   "Basic Design Safeguards /5"):
        out[column] = pd.to_numeric(out[column], errors="coerce").astype("Float64")
    return out
