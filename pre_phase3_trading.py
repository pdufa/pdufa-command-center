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
    "Drug", "Indication", "NCT ID", "Verification Status", "Protocol Last Checked",
    "Registry Milestone State", "Registry Primary Completion",
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


def research_discovery_pool(broad, strict, protocols, as_of):
    """Show research leads when fresh exact-NCT clinical verification is overdue.

    Do not label stale registry entries confirmed unreleased or entry-ready.
    Exclude trials a saved exact-NCT protocol explicitly marks inactive or posted.
    """
    if broad is None or broad.empty:
        return pd.DataFrame(columns=[
            *(list(broad.columns) if isinstance(broad, pd.DataFrame) else []),
            "Verification Status", "Protocol Last Checked",
        ])
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    strict_by_nct = (
        {str(r["NCT ID"]): r.to_dict() for _, r in strict.iterrows()}
        if strict is not None and not strict.empty else {}
    )
    by_nct = {}
    if protocols is not None and not protocols.empty and "nct_id" in protocols:
        for _, p in protocols.iterrows():
            nct = str(p.get("nct_id", "")).strip().upper()
            checked = str(p.get("checked_at", "")).strip()[:10]
            if (re.fullmatch(r"NCT[0-9]{8}", nct) and checked
                    and checked <= as_of.isoformat()
                    and (nct not in by_nct
                         or checked >= str(by_nct[nct].get("checked_at", ""))[:10])):
                by_nct[nct] = p.to_dict()
    active = {"RECRUITING", "ACTIVE_NOT_RECRUITING",
              "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
    records = []
    for _, trial in broad.iterrows():
        nct = str(trial.get("NCT ID", "")).strip().upper()
        proto = by_nct.get(nct)
        checked = str(proto.get("checked_at", ""))[:10] if proto else ""
        same_nct_source = (
            proto is not None and str(proto.get("source_url", "")).strip()
            == "https://clinicaltrials.gov/study/" + nct
        )
        if same_nct_source and (
            str(proto.get("registry_results_first_posted", "")).strip()
            or str(proto.get("registry_overall_status", "")).upper() not in active
        ):
            continue
        verified = strict_by_nct.get(nct)
        item = verified.copy() if verified is not None else trial.to_dict()
        item["Verification Status"] = (
            "FRESH REGISTRY — ISSUER READOUT NOT VERIFIED"
            if verified is not None
            else "RECHECK REQUIRED — PROTOCOL STALE OR UNVERIFIED"
        )
        item["Protocol Last Checked"] = checked
        records.append(item)
    return pd.DataFrame(records) if records else pd.DataFrame(
        columns=[*broad.columns, "Verification Status", "Protocol Last Checked"]
    )

def trading_research_queue(candidates, as_of, lookahead_days=180):
    """Screen possible future registry completion windows, never issuer readouts.

    This is a discovery shortlist. No publication, pre-readout or entry
    qualification is inferred from active registry status.
    """
    if lookahead_days not in ("ALL", 90, 180, 365):
        raise ValueError("lookahead_days must be ALL, 90, 180 or 365")
    if isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    if not isinstance(as_of, date):
        raise ValueError("as_of must be a date")
    if candidates is None or candidates.empty:
        return pd.DataFrame(columns=SHORTLIST_COLUMNS)

    last_day = (as_of + timedelta(days=lookahead_days)
                if lookahead_days != "ALL" else None)
    records = []
    for _, item in candidates.iterrows():
        first, last, precision = _completion_bounds(item.get("Primary Completion", ""))
        if lookahead_days != "ALL" and (
            first is None or last < as_of or first > last_day
        ):
            continue
        milestone_state = (
            "DATE NOT VERIFIED" if first is None
            else "PAST — CHECK READOUT" if last < as_of
            else "POTENTIAL UPCOMING MILESTONE"
        )
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
            "Verification Status": str(item.get(
                "Verification Status",
                "RECHECK REQUIRED — UNVERIFIED RESEARCH LEAD"
            )).strip(),
            "Protocol Last Checked": str(item.get("Protocol Last Checked", "")).strip(),
            "Registry Milestone State": milestone_state,
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
            "_sort_date": first if first is not None and last >= as_of else date.max,
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
