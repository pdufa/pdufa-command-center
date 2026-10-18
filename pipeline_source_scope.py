"""Canonical Pipeline-origin policy for downstream SEC, FDA and GEM scans.

Source files may feed Pipeline intake, but only records present in the Pipeline
universe can appear downstream. Source/issuer evidence never creates a trial.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from pipeline_universe import load_universe, read_rows


def pipeline_origins(data_dir, today=None):
    """Read the same canonical Pipeline record IDs as the Pipeline tab."""
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    if isinstance(today, str):
        today = date.fromisoformat(today[:10])
    frame = load_universe(Path(data_dir), today=today)
    if frame.empty:
        return set(), {}
    return (
        set(frame["record_id"].astype(str)),
        {str(row["record_id"]): str(row["ticker"]).strip().upper()
         for row in frame.to_dict("records")},
    )


def gem_research_id(record, record_ids, pipeline_tickers):
    """Pre-Oct-15 GEM/GEM JR research admission: exact sourced identity,
    without requiring prior inclusion in the canonical Pipeline feed.

    This does NOT relax clinical, SEC, financing or trading-entry checks.
    If the exact ID is already in Pipeline with a conflicting ticker, reject
    it rather than borrow evidence from another issuer.
    """
    import re

    ticker = str(record.get("Ticker") or "").strip().upper()
    event = str(record.get("Exact event") or "").strip()
    nct = str(record.get("NCT ID") or "").strip().upper()
    if not ticker or not re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker):
        return ""
    if event:
        # Regulatory records carry the issuer ticker in the exact-event key.
        if not event.startswith(ticker + "|"):
            return ""
        identifier = "APPLICATION|" + event
    elif re.fullmatch(r"NCT\d{8}", nct):
        identifier = "TRIAL|" + nct
    else:
        return ""
    if identifier in record_ids:
        canonical = str(pipeline_tickers.get(identifier) or "").strip().upper()
        if canonical and canonical != ticker:
            return ""
    return identifier


def source_scope(data_dir, today=None):
    """Enumerate scan targets only after Pipeline has minted their identity."""
    root = Path(data_dir)
    record_ids, ticker_by_id = pipeline_origins(root, today=today)
    events = [
        row for row in read_rows(root / "pdufa_candidates.csv")
        if "APPLICATION|" + str(row.get("event_key") or "").strip() in record_ids
        and str(row.get("ticker") or "").strip().upper() ==
        ticker_by_id.get("APPLICATION|" + str(row.get("event_key") or "").strip())
    ]
    # Only issuer rows connected to Pipeline application events being scanned.
    # Other Pipeline stages are displayed NOT_CHECKED until an application exists.
    matched_tickers = {str(row.get("ticker") or "").strip().upper() for row in events}
    companies = [
        row for row in read_rows(root / "company_registry.csv")
        if str(row.get("ticker") or "").strip().upper() in matched_tickers
    ]
    return events, companies


def gem_pipeline_id(record, record_ids, pipeline_tickers):
    """Require exact Pipeline application/NCT identity and compatible company."""
    event = str(record.get("Exact event") or "").strip()
    if event:
        identifier = "APPLICATION|" + event
    else:
        nct = str(record.get("NCT ID") or "").strip().upper()
        identifier = "TRIAL|" + nct if nct else ""
    if not identifier or identifier not in record_ids:
        return ""
    # NCT alone never authorizes a cross-issuer stock-program join.
    claimed = str(record.get("Ticker") or "").strip().upper()
    canonical = str(pipeline_tickers.get(identifier) or "").strip().upper()
    if claimed and canonical and claimed != canonical:
        return ""
    return identifier
