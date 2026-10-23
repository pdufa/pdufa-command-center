"""Pure, read-only enrichment calculations. Never writes qualification or FS/FA."""
from __future__ import annotations

from datetime import date
from math import sqrt
from typing import Optional


def cash_runway_months(cash: Optional[float], quarterly_operating_cash_flow: Optional[float]) -> Optional[float]:
    """Uses negative quarterly operating cash flow as a simple burn proxy."""
    if cash is None or quarterly_operating_cash_flow is None or cash < 0:
        return None
    if quarterly_operating_cash_flow >= 0:
        return None  # Positive cash flow is not an infinite runway estimate.
    return round(cash / (-quarterly_operating_cash_flow / 3), 2)


def market_cap(price: Optional[float], shares: Optional[float]) -> Optional[float]:
    if price is None or shares is None or price < 0 or shares < 0:
        return None
    return price * shares


def dilution_pct(new_shares: Optional[float], post_issue_shares: Optional[float]) -> Optional[float]:
    if new_shares is None or post_issue_shares is None or post_issue_shares <= 0 or new_shares < 0 or new_shares > post_issue_shares:
        return None
    return round(100 * new_shares / post_issue_shares, 4)


def reward_risk_ratio(upside_pct: Optional[float], downside_pct: Optional[float]) -> Optional[float]:
    if upside_pct is None or downside_pct is None or upside_pct <= 0 or downside_pct >= 0:
        return None
    return round(upside_pct / abs(downside_pct), 4)


def days_until_event(event_date: Optional[date], as_of: date) -> Optional[int]:
    return (event_date - as_of).days if event_date is not None else None


def evidence_record(value, source_url: str, observed_at: str, retrieved_at: str, status: str = "verified") -> dict:
    """Attach provenance; caller must verify source authenticity before using 'verified'."""
    if status not in {"verified", "calculated", "estimated", "missing", "conflicting"}:
        raise ValueError("Invalid evidence status")
    if status == "verified" and (not source_url.startswith("https://") or not observed_at or not retrieved_at):
        raise ValueError("Verified evidence requires HTTPS source and dates")
    return {"value": value, "source_url": source_url, "observed_at": observed_at,
            "retrieved_at": retrieved_at, "status": status}
